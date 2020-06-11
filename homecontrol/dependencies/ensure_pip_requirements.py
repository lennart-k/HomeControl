"""Helper module to ensure that pip requirements are installed"""

import os
import sys
from subprocess import Popen
from typing import Iterable

from pkg_resources import DistributionNotFound, VersionConflict, require

from homecontrol.exceptions import PipInstallError


def package_installed(package: str) -> bool:
    """Checks if a package is installed"""
    try:
        require(package)
        return True
    except (DistributionNotFound, VersionConflict):
        return False


def install_for_user() -> bool:
    """Checks if a package should be installed only for the user"""
    return not (
        hasattr(sys, "real_prefix")       # venv, virtualenv
        or sys.base_prefix != sys.prefix  # venv
        or os.path.isfile("/.dockerenv")  # Docker
        or os.geteuid() == 0              # Root
    )


def ensure_packages(
        packages: Iterable[str],
        upgrade: bool = True,
        test_index: bool = False) -> None:
    """Ensures that a package is installed"""
    unsatisfied = {package for package in packages
                   if not package_installed(package)}
    if not unsatisfied:
        return
    env = os.environ.copy()
    args = [sys.executable, "-m", "pip", "install", *unsatisfied]
    if upgrade:
        args.append("--upgrade")
    if install_for_user():
        args.append("--user")
    if test_index:
        args.extend(["-i", "https://test.pypi.org/simple/"])
    subprocess = Popen(args, env=env)
    if subprocess.wait():
        raise PipInstallError(
            "An error occured when installing pip requirements")
