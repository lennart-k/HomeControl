SPEC = """
meta:
  name: Szenes
  description: Provides szene functionality
"""

class Module:
    async def init(self):
        data = self.core.cfg.get("szenes", [])
        self.szenes = {szene["alias"]: Szene(self, szene) for szene in data}

        @event("gather_automation_providers")
        async def on_gather_automation_providers(event, engine, callback):
            callback(action={"szene": self.provider_factory})

    def provider_factory(self, rule, engine):
        target = rule.data["action"]["target"]
        return self.szenes[target]


class Szene:
    """
    A Szene is a set of states that should be set and actions that should be executed when invoked
    """
    def __init__(self, module, data):
        self.core = module.core
        self.data = data
    
    async def invoke(self):
        for item_id, data in self.data.get("items", {}).items():
            item = self.core.item_manager.items[item_id]

            for state_name, value in data.get("states", {}).items():
                await item.states.set(state_name, value)

            for action_instruction in data.get("action", []):
                await item.actions.execute(action_instruction["name"], **action_instruction.get("data", {}))

    async def on_trigger(self, data):
        return await self.invoke()

class SzeneActionProvider:
    """An automation provider for szenes"""
    def __init__(self, module, rule, engine):
        self.rule = rule
        self.module = module
        self.engine = engine
        self.core = engine.core

    async def on_trigger(self, data):
        return await self.module.szenes[self.rule["trigger"]["target"]].invoke()
