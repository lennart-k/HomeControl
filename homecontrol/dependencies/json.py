"""JSON Encoder and Decoder"""

# pylint: disable=invalid-name,too-few-public-methods,import-self
import json
from datetime import datetime
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Type, cast

if TYPE_CHECKING:
    from homecontrol.core import Core


class JSONEncoder(json.JSONEncoder):
    """Custom JSONEncoder that also parses HomeControl types"""

    def __init__(self, core: "Core", *args, **kwargs):
        self.core = core
        super().__init__(*args, **kwargs)

    # pylint: disable=no-self-use,too-many-return-statements,method-hidden
    def default(self, o):
        """Encode custom types"""
        if isinstance(o, Enum):
            return o.value

        if isinstance(o, datetime):
            return o.isoformat()

        if hasattr(o, "dump"):
            return o.dump()

        return o


def dumps(obj, *, indent=None, sort_keys=False, core: "Core" = None, **kw):
    """
    Dumps an object into a JSON string with support
    for HomeControl's data types
    """
    return json.dumps(
        obj, cls=cast(Type[JSONEncoder], partial(JSONEncoder, core=core)),
        indent=indent, sort_keys=sort_keys, **kw)


def dump(obj, fp, *, indent=None, sort_keys=False, core: "Core" = None, **kw):
    """
    Dumps an object into a Writer with support for HomeControl's data types
    """
    return json.dump(
        obj, fp, cls=cast(Type[JSONEncoder], partial(JSONEncoder, core=core)),
        indent=indent, sort_keys=sort_keys, **kw)
