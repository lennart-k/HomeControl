import sys
import yaml
import importlib
import importlib.util
import os
from dependencies.entity_types import Module


class ModuleManager:
    def __init__(self, core):
        self.core = core
        self.loaded_modules = {}

    async def load_folder(self, path) -> [object]:
        """
        Loads every module in a folder
        """
        out = []
        for folder in os.listdir(path):
            if os.path.isdir(os.path.join(path, folder)):
                out.append(await self.load_module(os.path.join(path, folder), folder))

        return out

    async def load_module(self, path, name) -> (object, Exception):
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
            self.core.event_engine.broadcast("module_not_loaded", exception=e)
            return e

        cfg = yaml.load(open(cfg_path))
        spec = importlib.util.spec_from_file_location(name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        mod.event = self.core.event_engine.register
        mod.tick = self.core.tick_engine.tick
        sys.path.append(path)
        spec.loader.exec_module(mod)
        sys.path.append(path)
        if not hasattr(mod, "Module"):
            mod.Module = Module
        mod_obj = mod.Module.__new__(mod.Module)
        mod_obj.core = self.core
        mod_obj.meta = cfg.get("meta", {})
        mod_obj.name = name
        mod_obj.path = path
        mod_obj.adapters = {}
        mod_obj.items = {}
        mod_obj.adapter_specs = {}
        mod_obj.item_specs = {}
        mod_obj.mod = mod
        mod_obj.spec = cfg
        mod_obj.__init__()

        self.loaded_modules[name] = mod_obj
        await self.core.entity_manager.add_from_module(mod_obj)
        if hasattr(mod_obj, "init"):
            await mod_obj.init()
        # self.core.event_engine.trigger("init", mod_obj)
        return mod_obj

    async def unload_module(self, name) -> None:
        """
        First removes all the adapters and items the module offers.
        Then it triggers the stop-coro and fully removes it.
        """
        for identifier in self.loaded_modules[name].items.keys():
            await self.core.entity_manager.remove_item(identifier)
        if hasattr(self.loaded_modules[name], "stop"):
            self.core.event_engine.trigger("stop", self.loaded_modules[name])
        del self.loaded_modules[name]
