"""ActionEngine for HomeControl"""

from homecontrol.dependencies.entity_types import Item


# pylint: disable=too-few-public-methods
class ActionEngine:
    """Holds available actions for an item"""
    def __init__(self, item: Item, core):
        self.core = core
        self.item = item
        self.actions = {}
        for action_name, method_name in item.spec.get("actions", {}).items():
            self.actions[action_name] = getattr(item, method_name)

    async def execute(self, name: str, *args, **kwargs) -> bool:
        """Executes an action, optionally with parameters"""
        if name in self.actions:
            await self.actions[name](*args, **kwargs)
            return True
        return False
