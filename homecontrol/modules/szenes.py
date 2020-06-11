"""Szenes for HomeControl"""

import logging

import voluptuous as vol

SPEC = {
    "name": "Szenes",
    "description": "Provides szene functionality"
}

CONFIG_SCHEMA = vol.Schema([
    vol.Schema({
        vol.Required("alias"): str,
        vol.Optional("items", default=[]): vol.Schema({
            vol.Optional("action", default=[]): [
                vol.Schema({
                    vol.Required("name"): str,
                    vol.Optional("data"): object
                })
            ],
            vol.Optional("states", default=dict): vol.Schema({
                str: str
            })
        })
    })
])

LOGGER = logging.getLogger(__name__)


class Module:
    """The Szene module holding the szene settings"""
    async def init(self) -> None:
        """Initialise the szenes"""
        self.cfg = await self.core.cfg.register_domain(
            "szenes",
            schema=CONFIG_SCHEMA,
            default=[],
            handler=self,
            allow_reload=True)
        self.szenes = {szene["alias"]: Szene(self, szene)
                       for szene in self.cfg}

        @self.core.event_engine.register("gather_automation_providers")
        async def on_gather_automation_providers(event, engine, callback):
            callback(action={"szene": self.provider_factory})

    def provider_factory(self, rule, engine) -> "Szene":
        """Returns a szene as an action provider for the automation module"""
        return SzeneActionProvider(
            name=rule.data["action"]["target"],
            module=self)

    async def invoke_szene(self, name: str) -> bool:
        """Invokes a szene by name"""
        if name in self.szenes:
            await self.szenes[name].invoke()
            return True
        return False

    async def apply_new_configuration(self, domain, config: list) -> None:
        """Applies a new configuration"""

        self.cfg = config
        self.szenes = {szene["alias"]: Szene(self, szene) for szene in config}
        LOGGER.info("Applied new szene configuration")


class SzeneActionProvider:
    """
    A wrapper for invoke_szene to properly handle config reloads
    """

    def __init__(self, name: str, module: Module) -> None:
        self.name = name
        self.module = module

    async def on_trigger(self, data: dict) -> bool:
        """Handles an automation trigger"""
        return await self.module.invoke_szene(self.name)


class Szene:
    """
    A Szene is a set of states that should be set
    of triggers and actions that should be executed when invoked
    """

    def __init__(self, module, data):
        self.core = module.core
        self.data = data

    async def invoke(self):
        """Invoke the szene"""
        for item_id, data in self.data.get("items", {}).items():
            item = self.core.item_manager.items[item_id]

            for state_name, value in data.get("states", {}).items():
                await item.states.set(state_name, value)

            for action_instruction in data.get("action", []):
                await item.actions.execute(
                    action_instruction["name"],
                    **action_instruction.get("data", {}))
