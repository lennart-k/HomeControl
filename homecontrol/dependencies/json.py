"""JSON Encoder and Decoder"""

# pylint: disable=invalid-name,too-few-public-methods,import-self
import json
from functools import partial
from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from homecontrol.core import Core
from homecontrol.dependencies.data_types import type_set, types
from homecontrol.dependencies.entity_types import (
    Item,
)
from homecontrol.exceptions import (
    ItemNotFoundException,
)
from homecontrol.dependencies.entity_types import (
    ITEM_SCHEMA
)


class JSONEncoder(json.JSONEncoder):
    """Custom JSONEncoder that also parses HomeControl types"""

    def __init__(self, core: "Core", *args, **kwargs):
        self.core = core
        super().__init__(*args, **kwargs)

    # pylint: disable=no-self-use,too-many-return-statements,method-hidden
    def default(self, o):
        """Encode custom types"""
        if isinstance(o, Item):
            return {
                "!type": "Item",
                "item_type": o.type,
                "id": o.identifier,
                "name": o.name
            }

        if isinstance(o, Enum):
            return o.value

        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, tuple(type_set)):
            return {
                "!type": type(o).__name__,
                "data": o.dump()
            }

        if hasattr(o, "dump"):
            return o.dump()

        return o


class JSONDecoder(json.JSONDecoder):
    """Custom JSONDecoder with object_hook"""

    def __init__(self, core: "Core", *args, **kwargs):
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

            if obj["!type"] in types:
                return types[obj["!type"]].from_data(obj["data"])
        return obj


def loads(s, *, encoding=None, parse_float=None,
          parse_int=None, parse_constant=None,
          object_pairs_hook=None, core: "Core" = None, **kw):
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
         core: "Core" = None, **kw):
    """
    Loads a Reader with a custom JSONDecoder
    that supports HomeControl's data types.
    Note that for items you need to specify the core parameter
    """
    return loads(fp.read(),
                 parse_float=parse_float, parse_int=parse_int,
                 parse_constant=parse_constant,
                 object_pairs_hook=object_pairs_hook, **kw)


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=True, indent=None, separators=None, sort_keys=False,
          core: "Core" = None, **kw):
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
         core: "Core" = None, **kw):
    """
    Dumps an object into a Writer with support for HomeControl's data types
    """
    return json.dump(obj, fp, skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                     check_circular=check_circular,
                     cls=partial(JSONEncoder, core=core),
                     allow_nan=allow_nan, indent=indent,
                     separators=separators, sort_keys=sort_keys, **kw)
