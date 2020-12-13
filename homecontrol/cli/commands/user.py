"""The user command"""
import argparse
from typing import TYPE_CHECKING
from .command import Command
from homecontrol.auth import AuthManager
import texttable
from getpass import getpass
if TYPE_CHECKING:
    from homecontrol.auth.credential_provider import CredentialProvider


class UserCommand(Command):
    """
    The user commands allows you to create and list users from the command-line
    """
    help = "manages users and their credentials"
    auth_manager: AuthManager

    async def run(self) -> None:
        """Entrypoint for the user command"""
        self.auth_manager = AuthManager(self.args.cfgdir, self.loop)
        await getattr(self, f"action_{self.args.action}")()

    async def action_list(self) -> None:
        """Lists the users"""
        users = self.auth_manager.users
        table = texttable.Texttable()
        table.add_row(
            ["name", "id", "owner", "system_generated", "credentials"])
        table.add_rows([[
            user.name, user.id, user.owner, user.system_generated, ", ".join(
                user.credentials.keys())
        ] for user in users.values()], header=False)
        print(table.draw())

    async def action_create(self) -> None:
        """Creates a user"""
        username = self.args.name
        user_id = self.args.id
        is_owner = self.args.owner
        password = self.args.password or getpass(
            f"Choose a password for user {username} (optional): ")
        table = texttable.Texttable()
        table.add_row([
            "name", "id", "owner", "system_generated", "credentials"
        ])
        table.add_row([
            username, user_id or "generated",
            is_owner, False, password and "password"
        ])
        user = await self.auth_manager.create_user(
            username, owner=is_owner, user_id=user_id
        )
        if password:
            password_provider: "CredentialProvider" = (
                self.auth_manager.credential_providers["password"])
            await password_provider.create_credentials(
                user, password)
            await self.auth_manager.users.storage.save_data(
                self.auth_manager.users.dict)
        print(table.draw())

    @staticmethod
    def add_args(parser: argparse.ArgumentParser) -> None:
        action_parser = parser.add_subparsers(dest="action", required=True)
        action_parser.add_parser("list")
        create_parser = action_parser.add_parser("create")
        create_parser.add_argument("name", type=str)
        create_parser.add_argument("--owner", action="store_true")
        create_parser.add_argument("--id", type=str)
        create_parser.add_argument("--password", type=str)
