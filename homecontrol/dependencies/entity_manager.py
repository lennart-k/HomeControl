import asyncio
from dependencies.state_engine import StateEngine
from dependencies.action_engine import ActionEngine
from dependencies.entity_types import Item
from const import (
    WORKING,
    NOT_WORKING,
    STOPPED
)


class EntityManager:
    def __init__(self, core):
        self.core = core
        self.items = {}
        self.item_specs = {}

    async def add_from_module(self, mod_obj):
        """
        Adds the adapter and item specs of a module to the dict of available ones
        """
        for name, spec in mod_obj.spec.get("items", {}).items():
            spec["class"] = type(name, (getattr(mod_obj.mod, name), Item), {})
            spec["module"] = mod_obj
            self.item_specs[f"{mod_obj.name}.{name}"] = spec
            mod_obj.item_specs[name] = spec

    async def remove_item(self, identifier: str):
        item = self.items[identifier]
        await asyncio.gather(*[self.core.loop.create_task(dependant_item.stop()) for dependant_item in item.dependant_items if hasattr(dependant_item, "stop")])
        for dependant_item in item.dependant_items:
            dependant_item.status = STOPPED
        for dependency in item.depends_on:
            dependency.dependant_items.remove(item)
        del self.items[identifier]

    async def create_item(self, identifier: str, item_type: str, cfg: dict) -> Item:
        spec = self.item_specs[item_type]
        item = spec["class"].__new__(spec["class"])
        item.type = item_type
        item.core = self.core
        item.spec = spec
        item.module = spec["module"]
        item.status = WORKING
        item.identifier = identifier
        item.dependant_items = set()  # Items that will depend on this one
        item.depends_on = set()  # Items this new item depends on
        config = {}
        for name, info in spec.get("config_fields", {}).items():
            config[name] = info.get("default", None)

        for key, value in list(cfg.items()):
            if type(value) == str:
                if value.startswith("i!"):
                    i = self.items.get(value[2:], None)
                    cfg[key] = i
                    # The new item being created depends on the other item:
                    # These dependencies matter to remove the items in the correct order
                    if i:
                        item.depends_on.add(i)
                        i.dependant_items.add(item)
                    else:
                        item.status = NOT_WORKING

        config.update(cfg)
        item.cfg = config
        item.states = StateEngine(item, self.core)
        item.actions = ActionEngine(item, self.core)
        item.__init__()
        if hasattr(item, "init"):
            await item.init()

        self.items[identifier] = item
        spec["module"].items[identifier] = item
        self.core.event_engine.broadcast("item_created", item=item)
        return item
