import sys
import importlib
import importlib.util
import os
from dependencies.yaml_loader import YAMLLoader
from dependencies.entity_types import Module


class ModuleManager:
    def __init__(self, core):
        self.core = core
        self.loaded_modules = {}

    async def load_folder(self, path: str) -> [object]:
        """
        Loads every module in a folder
        """
        out = []
        blacklist = self.core.cfg.get("module-manager", {}).get("blacklist", [])
        for node in os.listdir(path):
            if node == "__pycache__":
                continue
            mod_path = os.path.join(path, node)
            mod_name = node if os.path.isdir(node) else ".".join(os.path.splitext(node)[:-1])

            if not mod_name in blacklist:
                if os.path.isdir(mod_path):
                    out.append(await self.load_module(mod_path, mod_name))

                elif os.path.isfile(mod_path) and node.endswith(".py"):
                    out.append(await self.load_file_module(mod_path, mod_name))

        return out

    async def load_file_module(self, mod_path: str, name: str) -> (Module, Exception):
        """
        Loads a module from a file and send an init trigger
        """
        try:
            assert os.path.isfile(mod_path)
        except AssertionError as e:
            self.core.event_engine.broadcast("module_not_loaded", exception=e)
            return e

        spec = importlib.util.spec_from_file_location(name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        mod.event = self.core.event_engine.register
        mod.tick = self.core.tick_engine.tick
        spec.loader.exec_module(mod)
        if not hasattr(mod, "Module"):
            mod.Module = type("Module_"+name, (Module,), {})
        else:
            mod.Module = type("Module_"+name, (mod.Module, Module), {})

        cfg = (mod.SPEC if isinstance(mod.SPEC, dict) else YAMLLoader.load(mod.SPEC)) if hasattr(mod, "SPEC") else {}

        mod_obj = mod.Module.__new__(mod.Module)
        mod_obj.core = self.core
        mod_obj.meta = cfg.get("meta", {})
        mod_obj.name = name
        mod_obj.path = mod_path
        mod_obj.items = {}
        mod_obj.item_specs = {}
        mod_obj.mod = mod
        mod_obj.spec = cfg
        mod_obj.__init__()

        self.loaded_modules[name] = mod_obj
        await self.core.entity_manager.add_from_module(mod_obj)
        if hasattr(mod_obj, "init"):
            await mod_obj.init()
        return mod_obj


    async def load_module(self, path: str, name: str) -> (Module, Exception):
        """
        Loads a module from a folder and send an init trigger
        """
        mod_path = os.path.join(path, "module.py")
        cfg_path = os.path.join(path, "module.yaml")
        try:
            assert os.path.isdir(path)
            assert os.path.isfile(mod_path)
            assert os.path.isfile(cfg_path)
        except AssertionError as e:
            self.core.event_engine.broadcast("module_not_loaded", exception=e, name=name)
            return e

        cfg = YAMLLoader.load(open(cfg_path))
        
        spec = importlib.util.spec_from_file_location(name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        mod.event = self.core.event_engine.register
        mod.tick = self.core.tick_engine.tick
        sys.path.append(path)
        spec.loader.exec_module(mod)
        sys.path.append(path)
        if not hasattr(mod, "Module"):
            mod.Module = type("Module_"+name, (Module,), {})
        else:
            mod.Module = type("Module_"+name, (mod.Module, Module), {})

        mod_obj = mod.Module.__new__(mod.Module)
        mod_obj.core = self.core
        mod_obj.meta = cfg.get("meta", {})
        mod_obj.name = name
        mod_obj.path = path
        mod_obj.items = {}
        mod_obj.item_specs = {}
        mod_obj.mod = mod
        mod_obj.spec = cfg
        mod_obj.__init__()

        self.loaded_modules[name] = mod_obj
        await self.core.entity_manager.add_from_module(mod_obj)
        if hasattr(mod_obj, "init"):
            await mod_obj.init()
        self.core.event_engine.broadcast("module_loaded", module=mod_obj)
        return mod_obj

    async def unload_module(self, name: str) -> None:
        """
        First removes all the adapters and items the module offers.
        Then it triggers the stop-coro and fully removes it.
        """
        for identifier in self.loaded_modules[name].items.keys():
            await self.core.entity_manager.remove_item(identifier)
        if hasattr(self.loaded_modules[name], "stop"):
            self.core.event_engine.trigger("stop", self.loaded_modules[name])
        del self.loaded_modules[name]
