from dependencies.entity_types import Item

class ActionEngine:
    def __init__(self, item: Item, core):
        self.core = core
        self.item = item
        self.actions = {}
        for action_name, method_name in item.spec.get("actions", {}).items():
            self.actions[action_name] = getattr(item, method_name)

    async def execute(self, name: str, *args, **kwargs) -> bool:
        if name in self.actions:
            await self.actions[name](*args, **kwargs)
            return True
        return False
