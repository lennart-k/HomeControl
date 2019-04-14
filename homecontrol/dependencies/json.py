from dependencies.data_types import types
from dependencies.entity_types import (
    Module,
    Item
)
import json


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if Item in obj.__class__.__bases__:
            return {
                "!type": "Item",
                "item_type": obj.type,
                "id": obj.id
            }
        elif obj.__class__ in types.values():
            return {
                "!type": obj.__class.__name__,
                "data": obj.dump()
            }
        return obj


class JSONDecoder(json.JSONDecoder):
    def object_hook(self, obj):
        if "!type" in obj:
            if obj["!type"] in types:
                return types[obj["!type"]].from_data(obj["data"])
        return obj


def loads(s, *, encoding=None, parse_float=None,
          parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    return json.loads(s=s, encoding=encoding, parse_float=parse_float, cls=JSONDecoder,
                      parse_int=parse_int, parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)


def load(fp, *, parse_float=None,
         parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    return loads(fp.read(),
                 parse_float=parse_float, parse_int=parse_int,
                 parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=True, indent=None, separators=None, sort_keys=False, **kw):
    return json.dumps(obj, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
                      allow_nan=allow_nan, indent=indent, separators=separators, sort_keys=sort_keys, **kw)


def dump(obj, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True,
         allow_nan=True, indent=None, separators=None, sort_keys=False, **kw):
    return json.dump(obj, fp, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
                     allow_nan=allow_nan, indent=indent, separators=separators, sort_keys=sort_keys, **kw)

__all__ = ["loads", "load", "dumps", "dump"]
