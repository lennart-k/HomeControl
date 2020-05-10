"""Helper module to ensure that pip requirements are installed"""

import os
import sys
from subprocess import Popen
from pkg_resources import require, VersionConflict, DistributionNotFound

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
        or os.path.isfile("/.dockerenv")  # Docker
        or os.geteuid() == 0              # Root
    )

def ensure_packages(packages: str, upgrade: bool = True) -> None:
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
    subprocess = Popen(args, env=env)
    if subprocess.wait():
        raise PipInstallError(
            "An error occured when installing pip requirements")
