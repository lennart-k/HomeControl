"""Automation functionality"""

import asyncio
import logging

import voluptuous as vol

from homecontrol.core import Core
from homecontrol.const import EVENT_CORE_BOOTSTRAP_COMPLETE

LOGGER = logging.getLogger(__name__)

SPEC = {
    "name": "Automation"
}

CONFIG_SCHEMA = vol.Schema([
    {
        "alias": str,
        "trigger": vol.Schema({
            "provider": str
        }, extra=vol.ALLOW_EXTRA),
        "action": vol.Schema({
            "provider": str
        }, extra=vol.ALLOW_EXTRA)
    }
])


class EventTriggerProvider:
    """Trigger provider for events"""

    def __init__(self, rule, engine):
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]
        self.event_data = self.data.get("data", {})

        # Subscribe to trigger event
        self.core.event_engine.register(self.data["type"])(self.on_event)

    async def on_event(self, event: str, **kwargs) -> None:
        """Handle event"""
        if self.event_data.items() <= kwargs.items():
            await self.rule.on_trigger(kwargs)

    async def stop(self) -> None:
        """Stops the EventTriggerProvider for reload"""
        self.core.event_engine.remove_handler(self.data["type"], self.on_event)


class StateTriggerProvider:
    """Trigger provider for state changes"""

    def __init__(self, rule, engine):
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]

        # Subscribe to state changes
        self.core.event_engine.register("state_change")(self.on_state)

    async def on_state(self, event: str, item, changes: dict) -> None:
        """Handle new state"""
        if (item.identifier == self.data["target"]
                and self.data["state"] in changes):
            await self.rule.on_trigger({
                self.data["state"]: changes[self.data["state"]]
            })

    async def stop(self) -> None:
        """Stops the StateTriggerProvider for reload"""
        self.core.event_engine.remove_handler("state_change", self.on_state)


class TimerTriggerProvider:
    """A timer as a trigger provider"""
    def __init__(self, rule, engine) -> None:
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]

        self.core.tick_engine.tick(self.data["interval"])(self.trigger)

    async def trigger(self) -> None:
        """Trigger"""
        await self.rule.on_trigger({})

    async def stop(self) -> None:
        """Stop the provider"""
        self.core.tick_engine.remove_tick(self.data["interval"], self.trigger)


class StateActionProvider:
    """Action provider for states"""

    def __init__(self, rule, engine):
        self.engine = engine
        self.rule = rule
        self.core = engine.core

        self.data = rule.data["action"]

    async def on_trigger(self, data: dict) -> None:
        """Handle trigger"""
        target = self.core.item_manager.items.get(self.data["target"])
        changes = {
            **self.data.get("data", {}),
            **{key: data.get(ref)
               for key, ref in self.data.get("var-data", {}).items()}
        }

        LOGGER.debug("State action triggered %s %s",
                     changes, target.identifier)

        for state, value in changes.items():
            await target.states.set(state, value)


class ItemActionProvider:
    """Action provider that executes an action on an item"""

    def __init__(self, rule, engine):
        self.engine = engine
        self.rule = rule
        self.core = engine.core

        self.data = rule.data["action"]

    async def on_trigger(self, data: dict) -> None:
        """Handle trigger"""
        target = self.core.item_manager.items.get(self.data["target"])
        params = {
            **self.data.get("data", {}),
            **{key: data.get(ref)
               for key, ref in self.data.get("var-data", {}).items()}
        }

        await target.actions.execute(self.data["action"], **params)


class Module:
    """Automation module"""
    core: Core

    async def init(self):
        """Initialise the module"""
        self.trigger_providers = {
            "event": EventTriggerProvider,
            "state": StateTriggerProvider,
            "timer": TimerTriggerProvider
        }
        self.condition_providers = {

        }
        self.action_providers = {
            "state": StateActionProvider,
            "action": ItemActionProvider
        }
        self.rules = {}

        self.cfg = await self.core.cfg.register_domain(
            "automation",
            self,
            default=[],
            schema=CONFIG_SCHEMA,
            allow_reload=True
        ) or []

        self.core.event_engine.register(
            EVENT_CORE_BOOTSTRAP_COMPLETE)(self.start)

    async def start(self, event: str) -> None:
        """Start when core bootstrap is complete"""
        await self.core.event_engine.gather(
            "gather_automation_providers",
            engine=self,
            callback=self.register_automation_providers)
        await self.init_rules()

    async def init_rules(self) -> None:
        """Initialises the automation rules"""
        for rule in self.cfg:
            self.rules[rule["alias"]] = AutomationRule(rule, self)

    def register_automation_providers(self,
                                      trigger: dict = None,
                                      condition: dict = None,
                                      action: dict = None) -> None:
        """Register new automation providers"""
        self.trigger_providers.update(trigger or {})
        self.condition_providers.update(condition or {})
        self.action_providers.update(action or {})

    async def remove_rule(self, alias: str) -> None:
        """Removes an automation rule"""
        if alias in self.rules:
            await self.rules[alias].stop()
            del self.rules[alias]
            LOGGER.info("Automation rule '%s' removed", alias)

    async def stop(self) -> None:
        """Stops the Automation Engine"""
        LOGGER.info("Stopping the automation engine")
        await asyncio.gather(*[
            self.remove_rule(alias) for alias in self.rules
        ])

    async def apply_new_configuration(self, domain: str, config: list) -> None:
        """Applies new automation rules"""
        await self.stop()
        self.cfg = config
        await self.init_rules()


class AutomationRule:
    """Class representing an automation rule"""

    def __init__(self, data: dict, engine: Module):
        self.data = data
        self.engine = engine
        self.core = engine.core
        self.alias = data.get("alias", "Unnamed")

        self.trigger = self.engine.trigger_providers[
            data["trigger"]["provider"]](self, self.engine)
        self.action = self.engine.action_providers[
            data["action"]["provider"]](self, self.engine)

    async def on_trigger(self, data):
        """Handle trigger"""
        await self.action.on_trigger(data)

    async def stop(self) -> None:
        """Stops an automation rule"""
        if hasattr(self.trigger, "stop"):
            await self.trigger.stop()
