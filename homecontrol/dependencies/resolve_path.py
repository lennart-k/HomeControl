"""Helper module to resolve paths relative to the config folder"""

import os


def resolve_path(path: str, config_dir: str) -> str:
    """
    Resolves a path:
    ~/  for paths relative to your home directory
    /   for absolute paths
    anything else for paths relative to your config folder
    """
    if path.startswith("~"):
        return os.path.expanduser(path)
    if path.startswith("/"):
        return path
    return os.path.join(config_dir, path)
