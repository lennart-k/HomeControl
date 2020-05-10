"""ActionEngine for HomeControl"""

from typing import Callable, Union
from asyncio import iscoroutinefunction


def action(arg: Union[Callable, str]) -> Callable:
    """
    Decorator to mark a coroutine as an action

    >>> @action
    >>> async def foo(): ...

    >>> @action(name)
    >>> async def foo(): ...
    """
    def _decorator(action_func: Callable) -> Callable:
        action_func.action_name = arg
        return action_func

    if iscoroutinefunction(arg):
        arg.action_name = arg.__name__
        return arg

    return _decorator


# pylint: disable=too-few-public-methods
class ActionEngine:
    """Holds available actions for an item"""

    def __init__(
            self, item: "homecontrol.dependencies.entity_types.Item", core):
        self.core = core
        self.item = item
        self.actions = {}
        for attribute in dir(self.item):
            func = getattr(self.item, attribute)
            if hasattr(func, "action_name"):
                self.actions[getattr(func, "action_name")] = func

    async def execute(self, name: str, *args, **kwargs) -> bool:
        """Executes an action, optionally with parameters"""
        if name in self.actions:
            result = await self.actions[name](*args, **kwargs)
            if result is False:
                return False
            return True
        return False
