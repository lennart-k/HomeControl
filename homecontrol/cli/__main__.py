import argparse
import asyncio
import os

from .commands import COMMANDS


def parse_args() -> argparse.Namespace:
    """Parses the command-line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cfgdir", "-cd",
        default=os.path.expanduser("~/.homecontrol/"),
        help="Directory storing the HomeControl configuration")
    subparser = parser.add_subparsers(dest="command", required=True)
    for name, command in COMMANDS.items():
        command_parser = subparser.add_parser(
            name, help=command.help, description=command.description)
        command.add_args(command_parser)
    return parser.parse_args()


def main() -> None:
    """Main function getting called by command-line"""
    args = parse_args()
    loop = asyncio.get_event_loop()
    command = COMMANDS[args.command](args, loop)
    loop.run_until_complete(command.run())
