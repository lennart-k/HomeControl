"""WebSocket commands"""
# pylint: disable=relative-beyond-top-level
from homecontrol.modules.auth.decorator import needs_auth
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.event_engine import Event
from .command import WebSocketCommand


def add_commands(add_command):
    """Adds the commands"""
    add_command(PingCommand)
    add_command(WatchStatesCommand)


@needs_auth(owner_only=True)
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
        self.core.event_engine.register(
            "state_change")(self.on_state_change)
        return self.success("Now listening to state changes")

    async def on_state_change(
            self, event: Event, item: Item, changes: dict) -> None:
        self.send_message({
            "event": "state_change",
            "item": item.unique_identifier,
            "changes": changes
        })

    async def close(self) -> None:
        self.core.event_engine.remove_handler(
            "state_change", self.on_state_change)
