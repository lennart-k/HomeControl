"""HomeControl representation of ESPHome entities"""
from typing import TYPE_CHECKING, Any, Dict

import voluptuous as vol

from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef, StateProxy

if TYPE_CHECKING:
    from homecontrol.core import Core
    from .module import ESPHomeDevice
    from aioesphomeapi.model import (
        BinarySensorInfo, BinarySensorState,
        EntityInfo, EntityState,
        FanInfo, FanState,
        SensorInfo, SensorState,
        SwitchInfo, SwitchState)


class ESPHomeItem(Item):
    """HomeControl representation for esphome entities"""
    device: "ESPHomeDevice"
    entity: "EntityInfo"
    type: str = "esphome.ESPHomeItem"

    @classmethod
    async def constructor(
            cls, identifier: str, name: str,
            core: "Core", unique_identifier: str, device: "ESPHomeDevice",
            entity: "EntityInfo"
    ) -> "ESPHomeItem":
        item = cls()
        item.device = device
        item.entity = entity
        item.core = core
        item.identifier = identifier
        item.unique_identifier = unique_identifier
        item.name = name
        item.module = core.modules.esphome

        item.actions = {}
        item.states = StateProxy(item, core)

        return item

    def update_state(self, state: "EntityState") -> None:
        pass


class SwitchItem(ESPHomeItem):
    """An esphome switch"""
    entity: "SwitchInfo"

    on = StateDef()

    @on.setter(vol.Schema(bool))
    async def set_on(self, value: bool) -> Dict[str, Any]:
        """Sets the on state"""
        await self.device.api.switch_command(self.entity.key, value)
        return {}

    def update_state(self, state: "SwitchState") -> None:
        self.states.update("on", state.state)


class BinarySensorItem(ESPHomeItem):
    """An esphome binary_sensor"""
    entity: "BinarySensorInfo"

    on = StateDef()

    def update_state(self, state: "BinarySensorState") -> None:
        self.states.update("on", state.state)


class SensorItem(ESPHomeItem):
    """An esphome sensor"""
    entity: "SensorInfo"

    value = StateDef()

    def update_state(self, state: "SensorState") -> None:
        self.states.update("value", state.state)


class FanItem(ESPHomeItem):
    """An esphome fan"""
    entity: "FanInfo"

    on = StateDef()
    oscillating = StateDef()
    speed = StateDef()

    def update_state(self, state: "FanState") -> None:
        self.states.bulk_update(
            on=state.state,
            oscillating=state.oscillating,
            speed=state.speed
        )


ENTITY_TYPES = {
    "SwitchInfo": SwitchItem,
    "BinarySensorInfo": BinarySensorItem,
    "SensorInfo": SensorItem,
    "FanInfo": FanItem
}
