"""JSON Encoder and Decoder"""

# pylint: disable=invalid-name,too-few-public-methods,import-self
from typing import TYPE_CHECKING
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.data_types import type_set, types
if TYPE_CHECKING:
    from homecontrol.core import Core
from homecontrol.exceptions import ItemNotFoundException
import json
from functools import partial
from enum import Enum
from datetime import datetime


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
