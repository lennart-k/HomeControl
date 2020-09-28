"""WebSocket commands"""
# pylint: disable=relative-beyond-top-level
from collections import ChainMap
from typing import TYPE_CHECKING

import voluptuous as vol
from homecontrol.const import (ERROR_INVALID_ITEM_STATES, ERROR_ITEM_NOT_FOUND,
                               EVENT_ITEM_STATUS_CHANGED,
                               ITEM_ACTION_NOT_FOUND)
from homecontrol.dependencies.entity_types import Item, ItemStatus
from homecontrol.dependencies.event_bus import Event
from homecontrol.modules.auth.decorator import needs_auth

from .command import WebSocketCommand

if TYPE_CHECKING:
    from homecontrol.modules.auth.module import Module as AuthModule
    from homecontrol.modules.auth.auth.models import User


def add_commands(add_command):
    """Adds the commands"""
    add_command(PingCommand)
    add_command(WatchStatesCommand)
    add_command(WatchStatusCommand)
    add_command(AuthCommand)
    add_command(CurrentUserCommand)
    add_command(GetItemsCommand)
    add_command(GetModulesCommand)
    add_command(ActionCommand)
    add_command(SetStatesCommand)
    add_command(CoreShutdownCommand)
    add_command(CoreRestartCommand)
    add_command(GetUsersCommand)


class PingCommand(WebSocketCommand):
    """A basic ping command"""
    command = "ping"

    async def handle(self) -> None:
        """Handle the ping command"""
        return self.success("pong")


@needs_auth()
class WatchStatesCommand(WebSocketCommand):
    """Command to watch states"""
    command = "watch_states"

    async def handle(self) -> None:
        """Handle the watch_states command"""
        if self.command not in self.session.subscriptions:
            self.core.event_bus.register(
                "state_change")(self.on_state_change)

        self.session.subscriptions.add(self.command)
        return self.success("Now listening to state changes")

    async def on_state_change(
            self, event: Event, item: Item, changes: dict) -> None:
        """Handle the state_change event"""
        self.send_message({
            "event": "state_change",
            "item": item.unique_identifier,
            "changes": changes
        })

    async def close(self) -> None:
        """Remove the event listener"""
        self.core.event_bus.remove_handler(
            "state_change", self.on_state_change)


@needs_auth()
class WatchStatusCommand(WebSocketCommand):
    """Command to watch the item status"""
    command = "watch_status"

    async def handle(self) -> None:
        """Handle the watch_status command"""
        if self.command not in self.session.subscriptions:
            self.core.event_bus.register(
                EVENT_ITEM_STATUS_CHANGED)(self.on_status_change)

        self.session.subscriptions.add(self.command)
        return self.success("Now listening to status changes")

    async def on_status_change(
            self, event: Event, item: Item, previous: ItemStatus) -> None:
        """Handle the status_change event"""
        self.send_message({
            "event": "status_change",
            "item": item.unique_identifier,
            "previous": previous.value,
            "status": item.status.value
        })

    async def close(self) -> None:
        """Remove the event listener"""
        self.core.event_bus.remove_handler(
            EVENT_ITEM_STATUS_CHANGED, self.on_status_change)


class AuthCommand(WebSocketCommand):
    """Auth command"""
    command = "auth"
    schema = {
        vol.Required("token"): str
    }

    async def handle(self) -> None:
        """Handle the auth command"""
        token: str = self.data["token"]
        auth_manager = self.core.modules.auth.auth_manager

        refresh_token = await auth_manager.validate_access_token(token)

        if not refresh_token:
            return self.error("auth_invalid", "Invalid token")

        self.session.user = refresh_token.user

        return self.success("authenticated")


@needs_auth()
class CurrentUserCommand(WebSocketCommand):
    """Gives information about the current user"""
    command = "current_user"

    async def handle(self) -> None:
        """Handle the current_user command"""
        return self.success({
            "name": self.session.user.name,
            "owner": self.session.user.owner,
            "system_generated": self.session.user.system_generated,
            "id": self.session.user.id
        })


@needs_auth()
class GetItemsCommand(WebSocketCommand):
    """Returns information about the current items"""
    command = "get_items"

    async def handle(self) -> None:
        """Handle the get_items command"""
        return self.success([
            {
                "identifier": item.identifier,
                "unique_identifier": item.unique_identifier,
                "name": item.name,
                "type": item.type,
                "module": item.module.name,
                "status": item.status.value,
                "actions": list(item.actions.keys()),
                "states": await item.states.dump(),
                "implements": item.implements
            } for item in self.core.item_manager.items.values()
        ])


@needs_auth()
class GetModulesCommand(WebSocketCommand):
    """Returns information about the current modules"""
    command = "get_modules"

    async def handle(self) -> None:
        """Handle the get_modules command"""
        return self.success([
            {
                "name": module.name,
                "path": module.path,
                "spec": module.spec
            } for module in self.core.modules
        ])


@needs_auth()
class ActionCommand(WebSocketCommand):
    """Executes an item action"""
    command = "action"
    schema = {
        vol.Required("action"): str,
        vol.Required("item"): str,
        vol.Optional("kwargs"): dict
    }

    async def handle(self) -> None:
        """Handle the action command"""
        identifier = self.data["item"]
        action = self.data["action"]
        kwargs = self.data.get("kwargs", {})

        item = self.core.item_manager.get_item(identifier)
        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}")

        if item.status != ItemStatus.ONLINE:
            return self.error(
                "item_not_online",
                f"The item {item.identifier} is not online"
            )

        if action not in item.actions:
            return self.error(
                ITEM_ACTION_NOT_FOUND,
                f"Item {identifier} of type {item.type} "
                f"does not have an action {action}")

        try:
            return self.success({
                "result": await item.run_action(action, kwargs)
            })
        # pylint: disable=broad-except
        except Exception as err:
            return self.error(err)


@needs_auth()
class SetStatesCommand(WebSocketCommand):
    """Sets item states"""
    command = "set_states"
    schema = {
        vol.Required("item"): str,
        vol.Required("changes"): {
            str: object
        }
    }

    async def handle(self) -> None:
        """Handle the set_states command"""
        identifier = self.data["item"]
        changes = self.data["changes"]

        item = self.core.item_manager.get_item(identifier)
        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}")

        if changes.keys() - item.states.states.keys():
            return self.error(
                ERROR_INVALID_ITEM_STATES,
                f"States {changes.keys() - item.states.states.keys()}"
                "don't exist on item {item.name}"
            )

        if item.status != ItemStatus.ONLINE:
            return self.error(
                "item_not_online",
                f"The item {item.identifier} is not online"
            )

        try:
            result = dict(ChainMap(
                *[await item.states.set(state, value)
                  for state, value in changes.items()]))
            return self.success({
                "result": result
            })
        # pylint: disable=broad-except
        except Exception as err:
            return self.error(err)


@needs_auth(owner_only=True)
class CoreShutdownCommand(WebSocketCommand):
    """Shuts HomeControl down"""
    command = "core_shutdown"

    async def handle(self) -> None:
        """Handle the shutdown command"""
        self.core.loop.call_soon(self.core.shutdown)
        return self.success("Shutting down")


@needs_auth(owner_only=True)
class CoreRestartCommand(WebSocketCommand):
    """Shuts HomeControl down"""
    command = "core_restart"

    async def handle(self) -> None:
        """Handle the restart command"""
        self.core.loop.call_soon(self.core.restart)
        return self.success("Restarting")


@needs_auth(owner_only=True)
class GetUsersCommand(WebSocketCommand):
    """Returns the users"""
    command = "get_users"

    async def handle(self) -> None:
        """Handle the get_users command"""
        auth_module: "AuthModule" = self.core.modules.auth
        out = []
        for user in auth_module.auth_manager.users.values():
            user: "User" = user
            out.append({
                "name": user.name,
                "system_generated": user.system_generated,
                "identifier": user.id,
                "owner": user.owner
            })
        return self.success(out)
