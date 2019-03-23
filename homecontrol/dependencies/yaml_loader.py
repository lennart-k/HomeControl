from functools import partial
import voluptuous as vol
import yaml

from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.parser import Parser
from yaml.composer import Composer
from yaml.constructor import SafeConstructor, BaseConstructor
from yaml.resolver import Resolver

from dependencies.entity_types import (
    Item,
    Module
)
from exceptions import (
    ItemNotFoundException,
    NoCoreException
)


class Constructor(SafeConstructor):
    def __init__(self):
        self.add_multi_constructor("!vol/", self.__class__.vol_constructor)
        self.add_multi_constructor("!type/", self.__class__.type_constructor)
        SafeConstructor.__init__(self)

    def _obj(self, cls, node) -> object:
        if not node:
            return cls

        value = getattr(self, "construct_"+node.id)(node)
        
        if node.value == "":
            return cls
        elif type(value) == dict:
            return cls(**value)
        elif type(value) in (list, tuple):
            return cls(*value)
        else:
            return cls(value)

    def vol_constructor(self, suffix: str, node: yaml.Node = None) -> vol.Schema:
        return self._obj(getattr(vol, suffix), node)

    def type_constructor(self, suffix: str, node: yaml.Node = None) -> type:
        TYPES = {
            "bool": bool,
            "str": str,
            "int": int,
            "float": float,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "list": list,
            "complex": complex,
            "bytes": bytes,
            "object": object,
            # Custom types
            "Item": Item,
            "Module": Module,
        }
        if suffix in TYPES:
            return self._obj(TYPES.get(suffix), node)
        

class YAMLLoader(Reader, Scanner, Parser, Composer, Constructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)

    @classmethod
    def load(cls, data):
        loader = cls(data)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()
