"""Provides integration with iCloud devices"""
import asyncio
import os
from typing import TYPE_CHECKING, Any, Dict, cast

import voluptuous as vol
from pyicloud import PyiCloudService
from pyicloud.services.findmyiphone import AppleDevice

from homecontrol.const import ItemStatus
from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef, StateProxy

if TYPE_CHECKING:
    from homecontrol.core import Core


class ICloudDevice(Item):
    """An iCloud device that shall automatically be created by ICloudAccount"""
    account: "ICloudAccount"
    device: "AppleDevice"
    device_id: str
    update_task: asyncio.Task

    battery_level = StateDef()
    location = StateDef()

    async def init(self) -> None:
        self.update_task = self.core.loop.create_task(self._update_interval())

    async def _update_interval(self) -> None:
        while True:
            await self.update_states()
            await asyncio.sleep(30)

    @action("update")
    async def update_states(self) -> None:
        """Updates the states"""
        def _update() -> None:
            status = self.device.status()
            location = self.device.location()
            self.states.bulk_update(
                battery_level=round(status.get("batteryLevel", 0)*100),
                location={
                    "lon": location.get("longitude"),
                    "lat": location.get("latitude"),
                    "timestamp": location.get("timeStamp"),
                    "accuracy": location.get("horizontalAccuracy"),
                    "type": location.get("positionType")
                }
            )

        await self.core.loop.run_in_executor(None, _update)

    @action("play_sound")
    async def play_sound(self) -> None:
        """Plays a sound on the device"""
        await self.core.loop.run_in_executor(None, self.device.play_sound)

    # pylint: disable=arguments-differ
    @classmethod
    async def constructor(
            cls, identifier: str, name: str, core: "Core",
            unique_identifier: str, account: "ICloudAccount",
            device: "AppleDevice", device_id: str) -> "ICloudDevice":
        item = cls()

        item.identifier = identifier
        item.unique_identifier = unique_identifier
        item.name = name
        item.core = core

        item.actions = {}
        for attribute in dir(item):
            func = getattr(item, attribute)
            if hasattr(func, "action_name"):
                item.actions[getattr(func, "action_name")] = func

        item.states = StateProxy(item, core)

        item.account = account
        item.device = device
        item.device_id = device_id

        return item


class ICloudAccount(Item):
    """An iCloud account"""
    config_schema = vol.Schema({
        vol.Required("username"): str,
        vol.Optional("password"): str
    }, extra=vol.ALLOW_EXTRA)
    api: PyiCloudService
    entities: Dict[int, ICloudDevice]

    @classmethod
    async def constructor(
            cls, identifier: str, name: str, cfg: Dict[str, Any],
            state_defaults: Dict[str, Any], core: "Core",
            unique_identifier: str) -> Item:
        cfg = cast(Dict[str, Any], cls.config_schema(cfg or {}))

        item = cls()
        item.entities = {}
        item.core = core
        item.identifier = identifier
        item.unique_identifier = unique_identifier
        item.name = name
        item.cfg = cfg

        item.actions = {}

        item.states = StateProxy(item, core)
        item.status = ItemStatus.OFFLINE

        api = await core.loop.run_in_executor(
            None, PyiCloudService, cfg["username"], cfg.get("password"),
            os.path.join(core.cfg_dir, ".storage/icloud")
        )
        item.api = api

        devices = await core.loop.run_in_executor(None, lambda: api.devices)

        for device_id, device in devices.items():
            normalized_name = str(device).lower().replace(
                ' ', '_').replace(':', '')
            unique_e_identifier = f"{unique_identifier}_{normalized_name}"
            entity_identifier = f"{identifier}_{normalized_name}"

            entity_item = await ICloudDevice.constructor(
                identifier=entity_identifier,
                name=str(device),
                core=core,
                unique_identifier=unique_e_identifier,
                account=item,
                device=device,
                device_id=device_id
            )
            item.entities[device_id] = entity_item
            await core.item_manager.register_item(entity_item)

        return item
