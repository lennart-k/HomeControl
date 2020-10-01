"""action decorator for HomeControl items"""

from asyncio import iscoroutinefunction
from typing import Callable, Coroutine, Union, cast


def action(arg: Union[Callable, str]) -> Callable:
    """
    Decorator to mark a coroutine as an action

    >>> @action
    >>> async def foo(): ...

    >>> @action(name)
    >>> async def foo(): ...
    """
    def _decorator(action_func: Coroutine) -> Coroutine:
        setattr(action_func, "action_name", arg)
        return action_func

    if iscoroutinefunction(cast(Callable, arg)):
        setattr(arg, "action_name", cast(Coroutine, arg).__name__)
        return cast(Callable, arg)

    return _decorator
