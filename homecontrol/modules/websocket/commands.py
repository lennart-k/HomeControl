"""WebSocket commands"""
# pylint: disable=relative-beyond-top-level
import voluptuous as vol
from homecontrol.modules.auth.decorator import needs_auth
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.event_engine import Event
from .command import WebSocketCommand


def add_commands(add_command):
    """Adds the commands"""
    add_command(PingCommand)
    add_command(WatchStatesCommand)
    add_command(AuthCommand)
    add_command(CurrentUserCommand)
    add_command(GetItemsCommand)


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
        if not self.command in self.session.subscriptions:
            self.core.event_engine.register(
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
        self.core.event_engine.remove_handler(
            "state_change", self.on_state_change)


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
                "actions": list(item.actions.actions.keys()),
                "states": await item.states.dump()
            } for item in self.core.item_manager.items.values()
        ])
