"""ModuleManager module"""

import asyncio
import importlib
import importlib.util
import importlib.abc

import logging
import os
import sys
from types import ModuleType
from typing import (TYPE_CHECKING, Any, Dict, Iterator, Optional, Set, Type,
                    cast)

import pkg_resources
import voluptuous as vol

import homecontrol
from homecontrol.const import EVENT_MODULE_LOADED
from homecontrol.dependencies.ensure_pip_requirements import ensure_packages
from homecontrol.dependencies.entity_types import Module
from homecontrol.dependencies.yaml_loader import YAMLLoader
from homecontrol.exceptions import PipInstallError

if TYPE_CHECKING:
    from homecontrol.core import Core


LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required("folders", default=[]): [str],
    vol.Required("exclude", default=[]): [str],
    vol.Required("load-only", default=[]): [str],
    vol.Required("install-pip-requirements", default=True): bool,
    vol.Required("load-internal-modules", default=True): bool
})


class PythonModule(ModuleType):  # pylint: disable=too-few-public-methods
    """The Python module type with a resource_folder"""
    resource_folder: Optional[str]
    SPEC: Optional[Dict[str, Any]]
    Module: Module


# pylint: disable=too-few-public-methods
class ModuleFolder(ModuleType):
    """
    module folder representation to create
    a dummy package in sys.modules
    """

    def __init__(self, name: str) -> None:
        self.__name__ = name


class ModuleAccessor:
    """Wrapper for ModuleManager.loaded_modules"""

    _module_manager: "ModuleManager"

    def __init__(self, module_manager: "ModuleManager") -> None:
        self._module_manager = module_manager

    def __getattr__(self, name: str):
        return self._module_manager.loaded_modules.get(name)

    def __iter__(self) -> Iterator[Module]:
        return iter(self._module_manager.loaded_modules.values())


class ModuleLoader:
    """
    Takes care of module loading
    """
    load_after: Optional[Set[str]]
    _mod: Optional[PythonModule]
    _spec: Optional[Dict[str, Any]]
    _load_task: Optional[asyncio.Task]

    def __init__(self, core: "Core", mod_path: str, mod_name: str) -> None:
        self.mod_path = mod_path
        self.mod_name = mod_name
        self._mod = None
        self._spec = None
        self.core = core
        self._load_task = None
        self._spec, self._mod = self.spec()
        self.load_after = set(self._spec.get("load-after", []))

    def check_circular(self, mod_name: Optional[str] = None):
        """Checks for circular dependencies to prevent deadlocks"""
        mod_name = mod_name or self.mod_name
        for dependency in self.load_after:
            if dependency == mod_name:
                raise Exception(f"Circular import of {mod_name}")
            self.core.module_manager.module_loaders[dependency].check_circular(
                mod_name)

    def spec(self):
        """Returns the module's spec"""
        if os.path.isdir(self.mod_path):
            return self._folder_spec()
        return self._file_spec()

    def _folder_spec(self):
        spec_path = os.path.join(self.mod_path, "module.yaml")
        spec = (YAMLLoader.load(open(spec_path))
                if os.path.isfile(spec_path) else {})

        return spec, None

    def _file_spec(self):
        mod_spec = importlib.util.spec_from_file_location(
            self.mod_name, self.mod_path)
        mod = cast(PythonModule, importlib.util.module_from_spec(mod_spec))
        mod.resource_folder = None
        cast(importlib.abc.Loader, mod_spec.loader).exec_module(mod)

        spec = getattr(mod, "SPEC", {})

        return spec, mod

    async def load(self) -> Optional[Module]:
        """Loads a module"""
        self.check_circular()
        if not self._load_task:
            if os.path.isdir(self.mod_path):
                self._load_task = self.core.loop.create_task(
                    self._load_folder())
            else:
                self._load_task = self.core.loop.create_task(self._load_file())

        return await self._load_task

    async def _load_file(self) -> Optional[Module]:
        if not self._mod:
            self._file_spec()
        return await self._load_module()

    async def _load_folder(self) -> Optional[Module]:
        if not self._spec:
            self._folder_spec()
        spec = self._spec
        mod_path = os.path.join(self.mod_path, "module.py")
        try:
            ensure_packages(spec.get("pip-requirements", []))
            ensure_packages(
                spec.get("pip-test-requirements", []), test_index=True)
        except PipInstallError:
            return LOGGER.exception(
                "Module could not be loaded: %s at %s",
                self.mod_name, self.mod_path)

        mod_spec = importlib.util.spec_from_file_location(
            self.mod_name, mod_path,
            submodule_search_locations=[self.mod_path])
        mod = cast(PythonModule, importlib.util.module_from_spec(mod_spec))
        mod_folder = os.path.basename(os.path.dirname(self.mod_path))
        sys_mod_name = f"homecontrol_{mod_folder}.{self.mod_name}"
        mod.__package__ = sys_mod_name
        sys.modules[sys_mod_name] = mod
        mod.resource_folder = self.mod_path
        cast(importlib.abc.Loader, mod_spec.loader).exec_module(mod)
        self._spec.update(getattr(mod, "SPEC", {}))
        self._mod = mod
        return await self._load_module()

    async def _load_module(self) -> Module:
        if self.load_after:
            print(f"{self.mod_name} waiting for {self.load_after}")
            await asyncio.gather(*(
                self.core.module_manager.load_module(name)
                for name in self.load_after))
        mod, spec = self._mod, self._spec

        if not hasattr(mod, "Module"):
            mod.Module = cast(Module, type(
                "Module_" + self.mod_name, (Module,), {}))

        mod_obj: Module = mod.Module.__new__(cast(Type[Module], mod.Module))

        mod_obj.core = self.core
        mod_obj.resource_folder = mod.resource_folder
        mod_obj.name = self.mod_name
        mod_obj.path = self.mod_path
        mod_obj.mod = cast(PythonModule, mod)
        mod_obj.item_specs = {}
        mod_obj.spec = cast(Dict[str, Any], spec)
        mod_obj.__init__()

        self.core.module_manager.loaded_modules[self.mod_name] = mod_obj
        await self.core.item_manager.add_from_module(mod_obj)
        await mod_obj.init()
        LOGGER.info("Module %s loaded", self.mod_name)
        self.core.event_bus.broadcast(EVENT_MODULE_LOADED, module=mod_obj)
        return mod_obj


class ModuleManager:
    """Manages your modules"""

    cfg: dict
    loaded_modules: Dict[str, Module]
    module_loaders: Dict[str, ModuleLoader]
    module_accessor: ModuleAccessor

    def __init__(self, core: "Core"):
        self.core = core
        self.loaded_modules = {}
        self.module_loaders = {}
        self.module_accessor = ModuleAccessor(self)

    async def init(self) -> None:
        """Initialise the modules"""
        self.cfg = await self.core.cfg.register_domain(
            "modules",
            schema=CONFIG_SCHEMA,
            allow_reload=False)

        if self.cfg["load-internal-modules"]:
            internal_module_folder = pkg_resources.resource_filename(
                homecontrol.__name__, "modules")
            self.fetch_folder(internal_module_folder)

        for folder in self.cfg["folders"]:
            self.fetch_folder(folder)

        await asyncio.gather(*(
            module_loader.load()
            for module_loader in self.module_loaders.values()))

    def fetch_folder(self, path: str) -> None:
        """Fetches the modules from a folder"""
        exclude = self.cfg["exclude"]
        load_only = self.cfg["load-only"]

        package_name = f"homecontrol_{os.path.basename(path)}"
        sys.modules[package_name] = ModuleFolder(package_name)

        for node in os.listdir(path):
            if node.startswith("__"):
                continue
            mod_path = os.path.join(path, node)
            mod_name = node if os.path.isdir(
                node) else os.path.splitext(node)[0]

            if (mod_name in exclude
                    or (load_only and mod_name not in load_only)):
                continue

            self.module_loaders[mod_name] = ModuleLoader(
                self.core, mod_path, mod_name)

    async def load_module(self, name: str) -> Optional[Module]:
        """Loads a module"""
        if name not in self.module_loaders:
            LOGGER.error("Module %s does not exist", name)
            return None
        return await self.module_loaders[name].load()

    # pylint: disable=no-self-use
    def resource_path(self, module: Module, path: str = "") -> str:
        """
        Returns the path for a module's resource folder
        Note that only folder modules can have a resource path
        """
        assert module.resource_folder
        path = os.path.join(module.resource_folder, path)
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"Resource path {path} does not exist")

    async def stop(self) -> None:
        """Unloads all modules to prepare for a shutdown"""
        await asyncio.gather(*(
            module.stop()
            for module in self.loaded_modules.values()))

    def get_module(self, name: str) -> Optional[Module]:
        """Returns a loaded module by its name"""
        return self.loaded_modules.get(name)
