"""
Module containing the entity types
Every new Item or Module will get one of these classes as a base class
"""

from homecontrol.const import ItemStatus


class Item:
    """A dummy Item"""
    type: str
    identifier: str
    name: str
    status: ItemStatus = ItemStatus.OFFLINE

    def __repr__(self) -> str:
        return (f"<Item {self.type} identifier={self.identifier}"
                f"name={self.name}>")

    async def init(self) -> None:
        """Default init method"""
        return

    async def stop(self) -> None:
        """Default stop method"""
        return


class Module:
    """A dummy Module"""
    name: str
    folder_location: str = None
    items: dict
    spec: dict

    def __repr__(self) -> str:
        return f"<Module {self.name}>"

    async def init(self) -> None:
        """Default init method"""
        return

    async def stop(self) -> None:
        """Default stop method"""
        return
