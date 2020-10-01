"""Helper module to resolve paths relative to the config folder"""

import logging
import os
from typing import Optional, cast

LOGGER = logging.getLogger(__name__)


def resolve_path(path: str,
                 file_path: Optional[str] = None,
                 config_dir: Optional[str] = None) -> str:
    """
    Resolves a path:
    ~/  for paths relative to your home directory
    /   for absolute paths
    ./  for paths relative to the current file
    @/  for paths relative to your config folder
            only available if config_dir is specified
        for paths relative to the current file
    """
    relative_dir = os.path.abspath(cast(
        str,
        os.path.dirname(file_path) if file_path else config_dir))

    if path.startswith("~"):
        return os.path.expanduser(path)
    if path.startswith("/"):
        return path
    if path.startswith("./"):
        return os.path.join(relative_dir, path[2:])
    if path.startswith("@/"):
        if config_dir:
            return os.path.join(config_dir, path[2:])
        raise FileNotFoundError("Cannot use @/ paths without config_dir")
    return os.path.join(relative_dir, path)
