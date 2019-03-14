import re

class EventTriggerProvider:
    def __init__(self, engine):
        self.automation_engine = engine
        self.core = engine.core
        self.core.event_engine.register("*")(self.on_event)
        self.bindings = {}

    async def on_event(self, event, *args, **kwargs):
        rules = self.bindings.get(event, {})
        for rule, data in rules.items():
            params_list = data["params"]
            mapped_params = kwargs
            for key in kwargs:
                params_list.remove(key)

            mapped_params.update(dict(zip(params_list, args)))

            # "_" is a placeholder for unused parameters
            if "_" in mapped_params:
                del mapped_params["_"]

            await rule.on_trigger(self, mapped_params)
            

    def register(self, rule):
        event_data = re.match(r"^(?P<name>[^\(]+)(($)|\((?P<params>.*)\))$", rule.data["trigger"]["type"]).groupdict()
        event_name = event_data["name"]
        params = event_data["params"].replace(" ", "").split(",")
        if not event_name in self.bindings:
            self.bindings[event_name] = {}

        self.bindings[event_name][rule] = {
            "params": params
        }


class ValidateEventConditionProvider:
    def __init__(self, engine):
        self.automation_engine = engine
        self.core = engine.core

    async def condition_met(self, rule, event_data: dict) -> bool:
        pass

class StateActionProvider:
    def __init__(self, engine):
        self.automation_engine = engine
        self.core = engine.core

    async def do(self, event_data, action_data):
        target = self.core.entity_manager.items[action_data["target"]]

        for key, value in action_data["data"].items():
            await target.states.set(key, event_data[value] if value in event_data else value)


class AutomationEngine:
    def __init__(self, core):
        self.core = core
        self.trigger_providers = {
            "event": EventTriggerProvider(self)
        }
        self.condition_providers = {
            "validate-event": ValidateEventConditionProvider(self)
        }
        self.action_providers = {
            "state": StateActionProvider(self)
        }
        self.rules = set()

    def init_rules(self):
        for rule in self.core.cfg.get("automation", []):
            self.rules.add(AutomationRule(self.core, rule))

    # async def event_trigger_provider()

class AutomationRule:
    def __init__(self, core, data):
        self.core = core
        self.automation_engine = core.automation_engine
        self.data = data
        self.vars = data.get("data", {})
        self.alias = data.get("alias", "Unnamed")
        self.action_provider = self.automation_engine.action_providers[data["action"]["provider"]]
        self.automation_engine.trigger_providers[data["trigger"]["provider"]].register(self)

    async def on_trigger(self, provider, data):
        await self.action_provider.do(data, self.data["action"])