"""JSON Encoder and Decoder"""

# pylint: disable=invalid-name,too-few-public-methods,import-self
import json
from functools import partial
from enum import Enum

from homecontrol.core import Core
from homecontrol.dependencies.data_types import type_set, types
from homecontrol.dependencies.entity_types import (
    Item,
    Module
)
from homecontrol.exceptions import (
    ItemNotFoundException,
    ModuleNotFoundException
)
from homecontrol.const import (
    MODULE_SCHEMA,
    ITEM_SCHEMA
)


class JSONEncoder(json.JSONEncoder):
    """Custom JSONEncoder that also parses HomeControl types"""
    def __init__(self, core: Core, *args, **kwargs):
        self.core = core
        super().__init__(*args, **kwargs)

    # pylint: disable=no-self-use
    def default(self, obj):
        """Parse custom types"""
        if isinstance(obj, Item):
            return {
                "!type": "Item",
                "item_type": obj.type,
                "id": obj.identifier,
                "name": obj.name
            }
        if isinstance(obj, Module):
            return {
                "!type": "Module",
                "name": obj.name,
                "meta": obj.meta
            }
        if isinstance(obj, (BaseException, Exception)):
            return {
                "!type": "Exception",
                "type": type(obj).__name__,
                "message": str(obj)
            }
        if isinstance(obj, Enum):
            return obj.value

        # pylint: disable=unidiomatic-typecheck
        if isinstance(obj, tuple(type_set)):
            return {
                "!type": type(obj).__name__,
                "data": obj.dump()
            }

        if hasattr(obj, "dump"):
            return obj.dump()

        if not isinstance(
                obj, (type(None), bool, int, float, tuple, list, dict)):
            return obj.__dict__

        return obj


class JSONDecoder(json.JSONDecoder):
    """Custom JSONDecoder with object_hook"""
    def __init__(self, core: Core, *args, **kwargs):
        self.core = core
        super().__init__(*args, **kwargs, object_hook=self._object_hook)

    def _object_hook(self, obj):
        """Serialise json-incompatible objects"""
        if "!type" in obj:
            if obj["!type"] == "Item":
                ITEM_SCHEMA(obj)  # Check if obj has needed attributes
                # Check if item exists
                if not obj["id"] in self.core.item_manager.items:
                    raise ItemNotFoundException(
                        f"There's no item with id {obj['id']}")
                return self.core.item_manager.items[obj["id"]]

            if obj["!type"] == "Module":
                MODULE_SCHEMA(obj)  # Check if obj has needed attributes
                # Check if module exists
                if not obj["name"] in self.core.module_manager.loaded_modules:
                    raise ModuleNotFoundException(
                        f"There's no module with name {obj['name']}")
                return self.core.module_manager.loaded_modules[obj["name"]]

            if obj["!type"] in types:
                return types[obj["!type"]].from_data(obj["data"])
        return obj


def loads(s, *, encoding=None, parse_float=None,
          parse_int=None, parse_constant=None,
          object_pairs_hook=None, core: Core = None, **kw):
    """
    Loads a JSON string with a custom JSONDecoder
    that supports HomeControl's data types.
    Note that for items you need to specify the core parameter
    """
    return json.loads(s=s, encoding=encoding, parse_float=parse_float,
                      cls=partial(JSONDecoder, core=core),
                      parse_int=parse_int, parse_constant=parse_constant,
                      object_pairs_hook=object_pairs_hook, **kw)


def load(fp, *, parse_float=None,
         parse_int=None, parse_constant=None, object_pairs_hook=None,
         core: Core = None, **kw):
    """
    Loads a Reader with a custom JSONDecoder
    that supports HomeControl's data types.
    Note that for items you need to specify the core parameter
    """
    return loads(fp.read(),
                 parse_float=parse_float, parse_int=parse_int,
                 cls=partial(JSONDecoder, core=core),
                 parse_constant=parse_constant,
                 object_pairs_hook=object_pairs_hook, **kw)


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=True, indent=None, separators=None, sort_keys=False,
          core: Core = None, **kw):
    """
    Dumps an object into a JSON string with support
    for HomeControl's data types
    """
    return json.dumps(obj, skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                      check_circular=check_circular,
                      cls=partial(JSONEncoder, core=core),
                      allow_nan=allow_nan, indent=indent,
                      separators=separators, sort_keys=sort_keys, **kw)


def dump(obj, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True,
         allow_nan=True, indent=None, separators=None, sort_keys=False,
         core: Core = None, **kw):
    """
    Dumps an object into a Writer with support for HomeControl's data types
    """
    return json.dump(obj, fp, skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                     check_circular=check_circular,
                     cls=partial(JSONEncoder, core=core),
                     allow_nan=allow_nan, indent=indent,
                     separators=separators, sort_keys=sort_keys, **kw)


__all__ = ["loads", "load", "dumps", "dump"]
