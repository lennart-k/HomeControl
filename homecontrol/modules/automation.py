from homecontrol.core import Core
import logging

LOGGER = logging.getLogger(__name__)

SPEC = """
meta:
  name: Automation
  author: Lennart K
"""

class EventTriggerProvider:
    def __init__(self, rule, engine):
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]
        self.event_data = self.data.get("data", {})


        # Subscribe to trigger event
        event(self.data["type"])(self.on_event)
     
    async def on_event(self, event: str, **kwargs) -> None:

        if self.event_data.items() <= kwargs.items():
            await self.rule.on_trigger(kwargs)

class StateTriggerProvider:
    def __init__(self, rule, engine):
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]

        # Subscribe to state changes
        event("state_change")(self.on_state)

    async def on_state(self, event: str, item, changes: dict) -> None:
        if item.identifier == self.data["target"] and self.data["state"] in changes:
            await self.rule.on_trigger({self.data["state"]: changes[self.data["state"]]})

        

class StateActionProvider:
    def __init__(self, rule, engine):
        self.engine = engine
        self.rule = rule
        self.core = engine.core

        self.data = rule.data["action"]

    async def on_trigger(self, data: dict) -> None:
        target = self.core.entity_manager.items.get(self.data["target"])
        changes = {**self.data.get("data", {}), **{key: data.get(ref) for key, ref in self.data.get("var-data", {}).items()}}


        LOGGER.debug(f"State action triggered {changes} {target.identifier}")
        
        for state, value in changes.items():
            await target.states.set(state, value)

class ItemActionProvider:
    def __init__(self, rule, engine):
        self.engine = engine
        self.rule = rule
        self.core = engine.core

        self.data = rule.data["action"]

    async def on_trigger(self, data: dict) -> None:
        target = self.core.entity_manager.items.get(self.data["target"])
        params = {**self.data.get("data", {}), **{key: data.get(ref) for key, ref in self.data.get("var-data", {}).items()}}

        await target.actions.execute(self.data["action"], **params)

class Module:
    core: Core

    async def init(self):
        self.trigger_providers = {
            "event": EventTriggerProvider,
            "state": StateTriggerProvider
        }
        self.condition_providers = {
            
        }
        self.action_providers = {
            "state": StateActionProvider,
            "action": ItemActionProvider
        }
        self.rules = set()

        event("core_bootstrap_complete")(self.start)

    async def start(self, event: str) -> None:
        await self.core.event_engine.gather("gather_automation_providers", engine=self, callback=self.register_automation_providers)

        for rule in self.core.cfg.get("automation", []):
            self.rules.add(AutomationRule(rule, self))

    def register_automation_providers(self, trigger: dict = None, condition: dict = None, action: dict = None) -> None:
        self.trigger_providers.update(trigger or {})
        self.condition_providers.update(condition or {})
        self.action_providers.update(action or {})

class AutomationRule:
    def __init__(self, data: dict, engine: Module):
        self.data = data
        self.engine = engine
        self.core = engine.core
        self.alias = data.get("alias", "Unnamed")

        self.trigger = self.engine.trigger_providers[data["trigger"]["provider"]](self, self.engine)
        self.action = self.engine.action_providers[data["action"]["provider"]](self, self.engine)

    async def on_trigger(self, data):
        await self.action.on_trigger(data)
