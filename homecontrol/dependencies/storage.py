"""json based storage helper for homecontrol"""
import asyncio
import logging
import os
from datetime import datetime
from json import JSONDecodeError, dump, load
from shutil import copyfile
from typing import TYPE_CHECKING, Any, Callable, Optional, cast

import voluptuous as vol

if TYPE_CHECKING:
    from homecontrol.core import Core


LOGGER = logging.getLogger(__name__)

STORAGE_FOLDER = ".storage"

"""
File format:
storage.json

{
    data: {
        ...
    },
    name: "storage",
    last_update: "2019-09-20 22:31:34.682203"
    version: 1
}
"""

FILE_SCHEMA = vol.Schema({
    "data": vol.All(),
    "name": str,
    "last_update": vol.Coerce(datetime.fromisoformat),
    "version": int
})


class Storage:
    """JSON-file based data storage"""

    def __init__(self,
                 core: "Core",
                 name: str,
                 version: int,
                 storage_init: Optional[Callable] = None,
                 loader: Optional[Callable] = None,
                 dumper: Optional[Callable] = None,
                 migrator: Optional[Callable] = None) -> None:
        self.version = version
        self.storage_init = storage_init
        self.loader = loader
        self.dumper = dumper
        self.migrator = migrator
        self.core = core
        self._save_task: Optional[asyncio.Future] = None
        self.name = name
        self._data = None
        self.path = os.path.join(
            self.core.cfg_dir, STORAGE_FOLDER, f"{self.name}.json")

    def load_data(self) -> Any:
        """Loads data from the corresponding file"""
        data = None
        if self._data is not None:
            return self._data["data"]
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r") as file:
                    data = FILE_SCHEMA(load(file))
            except (vol.Error, JSONDecodeError):
                LOGGER.error(
                    "Storage data for storage %s invalid. "
                    "Backing up and resetting.",
                    self.name, exc_info=True)
                copyfile(self.path, self.path + ".backup")

        if data and data["version"] != self.version:
            if self.migrator:
                data = self.migrator(data)
            else:
                logging.warning(
                    "No migrator found for storage %s from version %s to %s",
                    self.name, data["version"], self.version)
                copyfile(self.path, self.path + ".backup")

        if not data:
            data = {
                "data": self.storage_init() if self.storage_init else None,
                "name": self.name,
                "last_update": datetime.utcnow(),
                "version": self.version,
            }

        if self.loader:
            data["data"] = self.loader(data["data"])

        self._data = data
        return self._data["data"]

    @property
    def last_update(self) -> Optional[datetime]:
        """Property to get the timestamp for the last update"""
        if not self._data:
            return None
        return self._data.get("last_update")

    @classmethod
    def get_storage(cls,
                    core: "Core",
                    name: str,
                    version: int,
                    storage_init: Optional[Callable] = None,
                    loader: Optional[Callable] = None,
                    dumper: Optional[Callable] = None
                    ) -> "Storage":
        """
        Loads a storage and returns it
        """
        storage = cls(
            core,
            name,
            version,
            storage_init,
            loader,
            dumper
        )
        storage.load_data()
        return storage

    def schedule_save(self, data: Any) -> asyncio.Task:
        """Saves the data"""
        return self.core.loop.create_task(self.save_data(data))

    async def save_data(self, data: Any) -> None:
        """Saves the data"""
        self._data = {
            "data": data if not self.dumper else self.dumper(data),
            "last_update": datetime.utcnow().isoformat(),
            "version": self.version,
            "name": self.name
        }
        if not self._save_task or self._save_task.done():
            self._save_task = cast(
                asyncio.Future, self.core.loop.run_in_executor(
                    None, self._save_data))

        return await self._save_task

    def _save_data(self) -> None:
        """Saves the current data"""
        storage_dir = os.path.dirname(self.path)
        if not os.path.isdir(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

        with open(self.path, "w") as file:
            dump(self._data, file, sort_keys=True, indent=4)


class DictWrapper(dict):
    """
    A dictionary wrapper for Storage
    """

    # pylint: disable=super-init-not-called
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.dict = storage.load_data()

    def schedule_save(self) -> asyncio.Task:
        """Schedules the current data to be saved"""
        return self.storage.schedule_save(self.dict)

    def __setitem__(self, key, item):
        self.dict[key] = item
        self.schedule_save()

    def __getitem__(self, key):
        return self.dict[key]

    def __repr__(self):
        return repr(self.dict)

    def __len__(self):
        return len(self.dict)

    def __delitem__(self, key):
        del self.dict[key]
        self.schedule_save()

    def get(self, key, default=None):
        return self.dict.get(key, default)

    def clear(self):
        self.dict.clear()
        self.schedule_save()

    def copy(self):
        return self.dict.copy()

    def update(self, *args, **kwargs):
        self.dict.update(*args, **kwargs)
        self.schedule_save()

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

    def pop(self, *args):
        result = self.dict.pop(*args)
        self.schedule_save()
        return result

    def setdefault(self, key, default):
        return self.dict.setdefault(key, default)

    def __contains__(self, item):
        return item in self.dict

    def __iter__(self):
        return iter(self.dict)

    def __eq__(self, value):
        return self.dict.__eq__(value)

    def __format__(self, format_spec):
        return self.dict.__format__(format_spec)

    def __ge__(self, value):
        return self.dict.__ge__(value)

    def __le__(self, value):
        return self.dict.__le__(value)

    def __lt__(self, value):
        return self.dict.__lt__(value)

    def __ne__(self, value):
        return self.dict.__ne__(value)
