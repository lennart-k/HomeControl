"""Provides a YAML loader"""

import itertools
import logging
import os

import yaml
from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from yaml.parser import Parser
from yaml.reader import Reader
from yaml.resolver import Resolver
from yaml.scanner import Scanner

import voluptuous as vol
from homecontrol.dependencies.resolve_path import resolve_path

LOGGER = logging.getLogger(__name__)

FORMAT_STRING_SCHEMA = vol.Schema({
    "template": str
}, extra=vol.ALLOW_EXTRA)


# pylint: disable=no-member,no-self-use
class Constructor(SafeConstructor):
    """Constructor for yaml"""

    name: str

    def __init__(self):
        self.add_constructor(
            "!format",
            self.__class__.format_string_constructor)
        self.add_constructor(
            "!include", self.__class__.include_file_constructor)
        self.add_constructor(
            "!include_merge", self.__class__.include_merge_constructor)
        self.add_constructor(
            "!include_dir_file_mapped",
            self.__class__.include_dir_file_mapped_constructor)
        self.add_constructor("!env_var", self.__class__.env_var_constructor)
        self.add_constructor("!path", self.__class__.path_constructor)
        self.add_constructor("!listdir", self.__class__.listdir_constructor)

        SafeConstructor.__init__(self)

    def _obj(self, cls, node: yaml.Node) -> object:
        if not node:
            return cls

        value = getattr(self, "construct_" + node.id)(node)

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
            raise TypeError("folder must be of type str")
        path = resolve_path(
            node.value, file_path=self.name, config_dir=self.cfg_folder)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)

        return self.__class__.load(open(path, "r"), cfg_folder=self.cfg_folder)

    def include_dir_file_mapped_constructor(self,
                                            node: yaml.Node = None) -> dict:
        """
        !include_dir_file_mapped <folder>

        Loads multiple files from a folder and maps their contents
        to their filenames
        """
        if not isinstance(node.value, str):
            raise TypeError("folder must be of type str")
        folder = resolve_path(
            node.value, file_path=self.name, config_dir=self.cfg_folder)
        if not os.path.isdir(folder):
            raise FileNotFoundError(folder)

        return {
            os.path.splitext(file)[0]: self.__class__.load(
                open(os.path.join(folder, file), "r"),
                cfg_folder=self.cfg_folder
            )
            for file in os.listdir(folder) if file.endswith(".yaml")
        }

    def include_merge_constructor(self,
                                  node: yaml.Node = None) -> (list, dict):
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
            raise TypeError("paths must be either of type str or list")

        paths = [
            resolve_path(path, file_path=self.name, config_dir=self.cfg_folder)
            for path in paths]

        files = set()
        for path in paths:
            if os.path.isfile(path):
                files.add(path)
            elif os.path.isdir(path):
                for file in os.listdir(path):
                    if file.endswith(".yaml"):
                        files.add(os.path.join(path, file))

        loaded_files = [
            self.__class__.load(
                open(file, "r"),
                cfg_folder=self.cfg_folder) for file in files]

        if not all(isinstance(loaded_file, type(loaded_files[0]))
                   for loaded_file in loaded_files):
            raise yaml.YAMLError(
                f"Cannot join {files}, they are not all "
                f"of type {type(loaded_files[0]).__name__}")

        if isinstance(loaded_files[0], list):
            return list(itertools.chain(*loaded_files))
        if isinstance(loaded_files[0], dict):
            return dict(itertools.chain(
                *[loaded_file.items() for loaded_file in loaded_files]))
        raise yaml.YAMLError(
            f"Unmergable type: {type(loaded_files[0]).__name__}")

    def path_constructor(self, node: yaml.Node) -> str:
        """
        !path <path>
        ~/  for paths relative to your home directory
        /   for absolute paths
        anything else for paths relative to your config folder
        """
        return resolve_path(
            node.value, file_path=self.name, config_dir=self.cfg_folder)

    def listdir_constructor(self, node: yaml.Node) -> list:
        """
        !listdir <path>

        Returns the contents of a directory
        """
        path = resolve_path(
            node.value, file_path=self.name, config_dir=self.cfg_folder)

        if os.path.isdir(path):
            return [os.path.join(path, item) for item in os.listdir(path)]
        return list()

    def env_var_constructor(self, node: yaml.nodes.Node) -> str:
        """
        Embeds an environment variable
        !env_var <name> [default]
        """
        args = node.value.split()

        if len(args) > 1:
            return os.getenv(args[0], default=" ".join(args[1:]))

        return os.environ[args[0]]

    def format_string_constructor(self,
                                  node: yaml.Node = None) -> str:
        """
        Renders a format string
        Example:
            !format { template: "Hello {who}", who: You }
        """
        mapping = FORMAT_STRING_SCHEMA(self.construct_mapping(node))

        return mapping["template"].format(**mapping)


# pylint: disable=too-many-ancestors
class YAMLLoader(Reader, Scanner, Parser, Composer, Constructor, Resolver):
    """Loads YAML with custom constructors"""

    def __init__(self, stream, cfg_folder: str = None):
        self.cfg_folder = cfg_folder
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)

    @classmethod
    def load(cls, data, cfg_folder: str = None):
        """Loads data"""
        loader = cls(data, cfg_folder=cfg_folder)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()
