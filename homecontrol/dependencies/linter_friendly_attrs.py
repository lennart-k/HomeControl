"""Helper module for linters not supporting attrs"""
from abc import ABC
from typing import TYPE_CHECKING


class LinterFriendlyAttrs(ABC):
    """A class that takes any arguments"""
    if TYPE_CHECKING:
        # pylint: disable=useless-super-delegation
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
