import itertools
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
        self.add_constructor("!include", self.__class__.include_file_constructor)
        self.add_constructor("!include_merge", self.__class__.include_merge_constructor)
        self.add_constructor("!include_dir_file_mapped", self.__class__.include_dir_file_mapped_constructor)
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

    def include_file_constructor(self, node: yaml.Node = None) -> object:
        """
        !include <path>
        ~/  for paths relative to your home directory
        /   for absolute paths
        anything else for paths relative to your config folder
        """
        if not isinstance(node.value, str):
            raise TypeError(f"folder must be of type str")
        path = resolve_path(node.value, os.path.dirname(self.name))
        if not os.path.isfile(path):
            raise FileNotFoundError(path)

        return self.__class__.load(open(path, "r"))

    def include_dir_file_mapped_constructor(self, node: yaml.Node = None) -> dict:
        """
        !include_dir_file_mapped <folder>
        
        Loads multiple files from a folder and maps their contents to their filenames
        """
        if not isinstance(node.value, str):
            raise TypeError(f"folder must be of type str")
        folder = resolve_path(node.value, os.path.dirname(self.name))
        if not os.path.isdir(folder):
            raise FileNotFoundError(path)

        return {
            os.path.splitext(file)[0]: self.__class__.load(open(os.path.join(folder, file), "r"))
            for file in os.listdir(folder) if file.endswith(".yaml")
        }

    def include_merge_constructor(self, node: yaml.Node = None) -> (list, dict):
        """
        !include <file|folder> ...

        Merges file or folder contents

        This constructor only works if all the files' contents are of same type
        and if this type is either list or dict.
        """
        paths = node.value
        if isinstance(paths, str):
            paths = paths.split(" ")
        elif not isinstance(paths, list):
            raise TypeError(f"paths must be either of type str or list")
        paths = [resolve_path(path, os.path.dirname(self.name)) for path in paths]
        files = set()
        for path in paths:
            if os.path.isfile(path):
                files.add(path)
            elif os.path.isdir(path):
                for file in os.listdir(path):
                    if file.endswith(".yaml"):
                        files.add(os.path.join(path, file))
        
        loaded_files = [self.__class__.load(open(file, "r")) for file in files]

        if not all(type(loaded_file) == type(loaded_files[0]) for loaded_file in loaded_files):
            raise yaml.YAMLError(f"Cannot join {files}, they are not all of type {type(loaded_files[0]).__name__}")

        if isinstance(loaded_files[0], list):
            return list(itertools.chain(*loaded_files))
        elif isinstance(loaded_files[0], dict):
            return dict(itertools.chain(*[loaded_file.items() for loaded_file in loaded_files]))

    def path_constructor(self, node: yaml.Node) -> str:
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
