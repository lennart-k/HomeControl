"""Helper module to ensure that pip requirements are installed"""

import sys
import subprocess
import json
from typing import Set

# pylint: disable=no-name-in-module,import-error
from pip._vendor.distlib.version import NormalizedMatcher

from homecontrol.exceptions import PipInstallError

INSTALLED_REQUIREMENTS = None


def ensure_pip_requirements(requirements: Set[str]) -> None:
    """Ensure that pip requirements are installed"""

    global INSTALLED_REQUIREMENTS  # pylint: disable=global-statement

    if INSTALLED_REQUIREMENTS is None:
        pip_list = subprocess.check_output(
            [sys.executable, "-m", "pip", "list", "--format=json",
             "--disable-pip-version-check"])

        INSTALLED_REQUIREMENTS = {
            item["name"]: item["version"] for item in json.loads(pip_list)}

    unsatisfied_requirements = set()

    for requirement in requirements:
        matcher = NormalizedMatcher(requirement)
        if matcher.name not in INSTALLED_REQUIREMENTS:
            unsatisfied_requirements.add(requirement)
            continue
        if not matcher.match(INSTALLED_REQUIREMENTS[matcher.name]):
            unsatisfied_requirements.add(requirement)

    if unsatisfied_requirements:
        process = subprocess.Popen([
            sys.executable, "-m", "pip", "install", *unsatisfied_requirements
        ])
        if process.wait():
            raise PipInstallError(
                "An error occured when installing pip requirements")
