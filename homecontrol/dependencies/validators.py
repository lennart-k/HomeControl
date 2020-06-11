"""Config validators"""
from typing import TYPE_CHECKING
import voluptuous as vol
if TYPE_CHECKING:
    from homecontrol.core import Core
    from homecontrol.dependencies.entity_types import Item


class IsItem:
    """A validator to get an item"""

    def __init__(self, core: "Core", msg: str = None) -> None:
        self.core = core
        self.msg = msg

    def __call__(self, identifier: str) -> "Item":
        if not isinstance(identifier, str):
            raise vol.Invalid(
                f"Item identifier has to be string, not {type(identifier)}")

        item = self.core.item_manager.get_item(identifier)
        if not item:
            raise vol.Invalid(
                self.msg.format(identifier=identifier)
                if self.msg
                else f"Item with identifier {identifier} does not exist")
        return item

    def __repr__(self):
        return f"IsItem"
