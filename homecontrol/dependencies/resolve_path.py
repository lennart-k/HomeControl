"""Helper module to resolve paths relative to the config folder"""

import os
import logging

LOGGER = logging.getLogger(__name__)


def resolve_path(path: str, file_path: str, config_dir: str = None) -> str:
    """
    Resolves a path:
    ~/  for paths relative to your home directory
    /   for absolute paths
    ./  for paths relative to the current file
    @/  for paths relative to your config folder
            only available if config_dir is specified
        for paths relative to the current file
    """
    if path.startswith("~"):
        return os.path.expanduser(path)
    if path.startswith("/"):
        return path
    if path.startswith("./"):
        return os.path.join(os.path.dirname(file_path), path[2:])
    if config_dir:
        if path.startswith("@/"):
            return os.path.join(config_dir, path[2:])
    return os.path.join(file_path, path)
