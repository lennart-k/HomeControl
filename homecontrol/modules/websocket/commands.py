"""WebSocket commands"""
# pylint: disable=relative-beyond-top-level
from .command import WebSocketCommand
from homecontrol.modules.auth.decorator import needs_auth


def add_commands(add_command):
    """Adds the commands"""
    add_command(PingCommand)


@needs_auth(owner_only=True)
class PingCommand(WebSocketCommand):
    """A basic ping command"""
    command = "ping"

    async def handle(self) -> None:
        """Handle the ping command"""
        return self.success(self.session.user.owner)
        return self.success("pong")
