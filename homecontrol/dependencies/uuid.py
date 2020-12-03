"""Generates a unique identifier for HomeControl"""
from typing import TYPE_CHECKING
from uuid import uuid4

from homecontrol.dependencies.storage import Storage

if TYPE_CHECKING:
    from homecontrol.core import Core


def get_uuid(core: "Core") -> str:
    """Returns an identifier for the HomeControl instance"""
    storage = Storage("uuid", 1, core=core, storage_init=lambda: uuid4().hex)
    return storage.load_data()
