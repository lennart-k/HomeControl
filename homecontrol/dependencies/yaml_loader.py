import os
import voluptuous as vol
import logging

import yaml
from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.parser import Parser
from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from yaml.resolver import Resolver

from homecontrol.dependencies.resolve_path import resolve_path
from homecontrol.dependencies.entity_types import (
    Item,
    Module
)

LOGGER = logging.getLogger(__name__)

def resolve_path(path: str, config_dir: str) -> str:
    if path.startswith("~"):
        return os.path.expanduser(path)
    elif path.startswith("/"):
        return path
    else:
        return os.path.join(config_dir, path)


class Constructor(SafeConstructor):
    def __init__(self):
        self.add_multi_constructor("!vol/", self.__class__.vol_constructor)
        self.add_multi_constructor("!type/", self.__class__.type_constructor)
        self.add_constructor("!include", self.__class__.file_include_constructor)
        self.add_constructor("!env_var", self.__class__.env_var_constructor)
        self.add_constructor("!path", self.__class__.path_constructor)
        
        SafeConstructor.__init__(self)

    def _obj(self, cls, node: yaml.Node) -> object:
        if not node:
            return cls

        value = getattr(self, "construct_"+node.id)(node)
        
        if node.value == "":
            return cls
        if isinstance(value, dict):
            return cls(**value)
        if isinstance(value, (list, tuple)):
            return cls(*value)

        return cls(value)

    def file_include_constructor(self, node: yaml.Node = None) -> object:
        """
        !include <path>
        ~/  for paths relative to your home directory
        /   for absolute paths
        anything else for paths relative to your config folder
        """
        path = resolve_path(node.value, os.path.dirname(self.name))
        return self.__class__.load(open(path, "r"))

    def path_constructor(self, node: yaml.Node = None) -> str:
        """
        !path <path>
        ~/  for paths relative to your home directory
        /   for absolute paths
        anything else for paths relative to your config folder
        """
        return resolve_path(node.value, os.path.dirname(self.name))

    def env_var_constructor(self, node: yaml.nodes.Node) -> str:
        """
        Embeds an environment variable
        !env_var <name> [default]
        """
        args = node.value.split()

        if len(args) > 1:
            return os.getenv(args[0], default=" ".join(args[1:]))

        return os.environ[args[0]]

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
