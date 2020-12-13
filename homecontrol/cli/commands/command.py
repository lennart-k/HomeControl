"""Provides a base class for HomeControl CLI commands"""
import argparse
from asyncio.events import AbstractEventLoop
from typing import Optional


class Command:
    """Base class for CLI commands"""
    args: argparse.Namespace
    help: Optional[str] = None
    description: Optional[str] = None

    def __init__(
            self, args: argparse.Namespace, loop: AbstractEventLoop) -> None:
        self.args = args
        self.loop = loop

    @staticmethod
    def add_args(parser: argparse.ArgumentParser) -> None:
        pass
