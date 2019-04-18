import json
from functools import partial
import voluptuous as vol

from core import Core
from dependencies.data_types import types
from dependencies.entity_types import (
    Item,
    Module
)
from exceptions import (
    ItemNotFoundException,
    ModuleNotFoundException
)
from const import (
    MODULE_SCHEMA,
    ITEM_SCHEMA
)


class JSONEncoder(json.JSONEncoder):
    def __init__(self, core: Core, *args, **kwargs):
        self.core = core
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if Item in obj.__class__.__bases__:
            return {
                "!type": "Item",
                "item_type": obj.type,
                "id": obj.identifier
            }
        elif Module in obj.__class__.__bases__:
            return {
                "!type": "Module",
                "name": obj.name,
                "meta": obj.meta
            }
        elif obj.__class__ in types.values():
            return {
                "!type": obj.__class.__name__,
                "data": obj.dump()
            }
        return obj


class JSONDecoder(json.JSONDecoder):
    def __init__(self, core: Core, *args, **kwargs):
        self.core = core
        super().__init__(*args, **kwargs, object_hook=self.object_hook)

    def object_hook(self, obj):
        if "!type" in obj:
            if obj["!type"] == "Item":
                ITEM_SCHEMA(obj)  # Check if obj has needed attributes
                # Check if item exists
                assert obj["id"] in self.core.entity_manager.items, ItemNotFoundException(
                    f"There's no item with id {obj['id']}")
                return self.core.entity_manager.items[obj["id"]]

            elif obj["!type"] == "Module":
                MODULE_SCHEMA(obj)  # Check if obj has needed attributes
                # Check if module exists
                assert obj["name"] in self.core.module_manager.loaded_modules, ModuleNotFoundException(
                    f"There's no module with name {obj['name']}"
                )
                return self.core.module_manager.loaded_modules[obj["name"]]

            elif obj["!type"] in types:
                return types[obj["!type"]].from_data(obj["data"])
        return obj


def loads(s, *, encoding=None, parse_float=None,
          parse_int=None, parse_constant=None, object_pairs_hook=None, core: Core = None, **kw):
    """
    Loads a JSON string with a custom JSONDecoder that supports HomeControl's data types.
    Note that for items you need to specify the core parameter
    """
    return json.loads(s=s, encoding=encoding, parse_float=parse_float, cls=partial(JSONDecoder, core=core),
                      parse_int=parse_int, parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)


def load(fp, *, parse_float=None,
         parse_int=None, parse_constant=None, object_pairs_hook=None, core: Core = None, **kw):
    """
    Loads a Reader with a custom JSONDecoder that supports HomeControl's data types.
    Note that for items you need to specify the core parameter
    """
    return loads(fp.read(),
                 parse_float=parse_float, parse_int=parse_int,
                 parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=True, indent=None, separators=None, sort_keys=False, core: Core = None, **kw):
    """
    Dumps an object into a JSON string with support for HomeControl's data types
    """
    return json.dumps(obj, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
                      cls=partial(JSONEncoder, core=core),
                      allow_nan=allow_nan, indent=indent, separators=separators, sort_keys=sort_keys, **kw)


def dump(obj, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True,
         allow_nan=True, indent=None, separators=None, sort_keys=False, core: Core = None, **kw):
    """
    Dumps an object into a Writer with support for HomeControl's data types
    """
    return json.dump(obj, fp, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
                     cls=partial(JSONEncoder, core=core),
                     allow_nan=allow_nan, indent=indent, separators=separators, sort_keys=sort_keys, **kw)


__all__ = ["loads", "load", "dumps", "dump"]
