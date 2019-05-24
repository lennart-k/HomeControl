"""ModuleManager module"""

import subprocess
import sys
import importlib
import importlib.util
import os
import json
import logging

import pkg_resources
from pip._vendor.distlib.version import NormalizedMatcher
import voluptuous as vol

import homecontrol
from homecontrol.dependencies.yaml_loader import YAMLLoader
from homecontrol.dependencies.entity_types import Module
from homecontrol.exceptions import PipInstallError

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required("folders", default=[]): [str],
    vol.Required("blacklist", default=[]): [str],
    vol.Required("install-pip-requirements", default=True): bool,
    vol.Required("load-internal-modules", default=True): bool
})


class ModuleManager:
    """Manages your modules"""

    cfg: dict

    def __init__(self, core):
        self.core = core
        self.loaded_modules = {}
        pip_list = subprocess.check_output(
            [sys.executable, "-m", "pip", "list",
             "--format=json", "--disable-pip-version-check"])
        self.installed_requirements = {
            item["name"]: item["version"] for item in json.loads(pip_list)}

    async def init(self) -> None:
        """Initialise the modules"""
        self.cfg = await self.core.cfg.register_domain(
            "module-manager", allow_reload=False)

        for folder in self.cfg["folders"]:
            await self.load_folder(folder)

        if self.cfg["load-internal-modules"]:
            internal_module_folder = pkg_resources.resource_filename(
                homecontrol.__name__, "modules")
            await self.load_folder(internal_module_folder)

    async def load_folder(self, path: str) -> [object]:
        """Load every module in a folder"""
        out = []
        blacklist = self.cfg.get("blacklist", [])
        for node in os.listdir(path):
            if node == "__pycache__":
                continue
            mod_path = os.path.join(path, node)
            mod_name = node if os.path.isdir(
                node) else ".".join(os.path.splitext(node)[:-1])

            if mod_name not in blacklist:
                if os.path.isdir(mod_path):
                    out.append(
                        await self.load_folder_module(mod_path, mod_name))

                elif os.path.isfile(mod_path) and node.endswith(".py"):
                    out.append(
                        await self.load_file_module(mod_path, mod_name))

        return out

    async def load_file_module(self,
                               mod_path: str,
                               name: str) -> (Module, Exception):
        """
        Loads a module from a file and initialises it

        Returns a Module object
        """
        try:
            assert os.path.isfile(mod_path)
        except AssertionError as error:
            LOGGER.warning(
                "Module could not be loaded: %s at %s", name, mod_path)
            self.core.event_engine.broadcast(
                "module_not_loaded", exception=error)
            return error

        spec = importlib.util.spec_from_file_location(name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        mod.resource_folder = None
        mod.event = self.core.event_engine.register
        mod.tick = self.core.tick_engine.tick
        spec.loader.exec_module(mod)
        if not hasattr(mod, "Module"):
            mod.Module = type("Module_" + name, (Module,), {})
        else:
            mod.Module = type("Module_" + name, (mod.Module, Module), {})

        cfg = (mod.SPEC if isinstance(mod.SPEC, dict) else YAMLLoader.load(
            mod.SPEC)) if hasattr(mod, "SPEC") else {}

        return await self._load_module_object(cfg, name, mod_path, mod)

    async def load_folder_module(self,
                                 path: str,
                                 name: str) -> (Module, Exception):
        """
        Loads a module from a folder and initialises it

        It also takes care of pip requirements

        Returns a Module object
        """
        mod_path = os.path.join(path, "module.py")
        cfg_path = os.path.join(path, "module.yaml")
        try:
            assert os.path.isdir(path)
            assert os.path.isfile(mod_path)
            assert os.path.isfile(cfg_path)
        except AssertionError as error:
            LOGGER.warning("Module could not be loaded: %s at %s", name, path)
            self.core.event_engine.broadcast(
                "module_not_loaded", exception=error, name=name)
            return error

        cfg = YAMLLoader.load(open(cfg_path))

        unsatisfied_pip_dependencies = set()
        for requirement in cfg.get("pip-requirements", []):
            matcher = NormalizedMatcher(requirement)
            if matcher.name not in self.installed_requirements:
                unsatisfied_pip_dependencies.add(requirement)
                continue
            if not matcher.match(self.installed_requirements[matcher.name]):
                unsatisfied_pip_dependencies.add(requirement)

        if unsatisfied_pip_dependencies:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install",
                 *unsatisfied_pip_dependencies])
            if process.wait():
                LOGGER.warning(
                    "Module could not be loaded: %s at %s", name, path)
                self.core.event_engine.broadcast(
                    "module_not_loaded",
                    exception=PipInstallError(),
                    name=name)
                return

        spec = importlib.util.spec_from_file_location(name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        mod.resource_folder = path
        mod.event = self.core.event_engine.register
        mod.tick = self.core.tick_engine.tick
        sys.path.append(path)
        spec.loader.exec_module(mod)
        sys.path.remove(path)
        return await self._load_module_object(cfg, name, path, mod)

    async def _load_module_object(self,
                                  cfg: dict,
                                  name: str,
                                  path: str,
                                  mod) -> Module:
        """
        Initialises a module object
        This method should only be invoked by ModuleManager
        """
        if not hasattr(mod, "Module"):
            mod.Module = type("Module_" + name, (Module,), {})
        else:
            mod.Module = type("Module_" + name, (mod.Module, Module), {})

        mod_obj = mod.Module.__new__(mod.Module)

        mod_obj.core = self.core
        mod_obj.meta = cfg.get("meta", {})
        mod_obj.resource_folder = mod.resource_folder
        mod_obj.name = name
        mod_obj.path = path
        mod_obj.items = {}
        mod_obj.item_specs = {}
        mod_obj.mod = mod
        mod_obj.spec = cfg
        mod_obj.__init__()

        self.loaded_modules[name] = mod_obj
        await self.core.item_manager.add_from_module(mod_obj)
        if hasattr(mod_obj, "init"):
            await mod_obj.init()
        self.core.event_engine.broadcast("module_loaded", module=mod_obj)
        return mod_obj

    async def unload_module(self, name: str) -> None:
        """
        First removes all the items the module offers.
        Then it triggers the stop-coro and fully removes it.
        """
        for identifier in self.loaded_modules[name].items.keys():
            await self.core.item_manager.remove_item(identifier)
        if hasattr(self.loaded_modules[name], "stop"):
            await self.loaded_modules[name].stop()
        del self.loaded_modules[name]

    async def stop(self) -> None:
        """Unloads all modules to prepare for a shutdown"""
        for module in list(self.loaded_modules.keys()):
            await self.unload_module(module)

    # pylint: disable=no-self-use
    def resource_path(self, module: Module, path: str = "") -> str:
        """
        Returns the path for a module's resource folder
        Note that only folder modules can have a resource path
        """
        path = os.path.join(module.resource_folder, path)
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"Resource path {path} does not exist")
