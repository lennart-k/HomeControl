"""Helper module to ensure that pip requirements are installed"""

import sys
import subprocess
from typing import Set
from pkg_resources import require, VersionConflict, DistributionNotFound

from homecontrol.exceptions import PipInstallError


def ensure_pip_requirements(requirements: Set[str]) -> None:
    """Ensure that pip requirements are installed"""
    unsatisfied = set()
    for requirement in requirements:
        try:
            require(requirement)
        except (DistributionNotFound, VersionConflict):
            unsatisfied.add(requirement)

    if unsatisfied:
        process = subprocess.Popen([
            sys.executable, "-m", "pip", "install", *unsatisfied])
        if process.wait():
            raise PipInstallError(
                "An error occured when installing pip requirements")
