"""action decorator for HomeControl items"""

from asyncio import iscoroutinefunction
from typing import Callable, Union


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
