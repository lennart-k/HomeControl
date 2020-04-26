"""Helper to find the pip requirements for a builtin module"""
import os
import pkg_resources

import homecontrol
from yaml.loader import SafeLoader
import yaml

MODULE_FOLDER = pkg_resources.resource_filename(
    homecontrol.__name__, "modules")

def get_requirements() -> list:
    """
    Lists the pip requirements for the builtin folder modules
    """
    output = []

    for node in os.listdir(MODULE_FOLDER):
        if node == "__pycache__":
            continue
        mod_path = os.path.join(MODULE_FOLDER, node)
        spec_path = os.path.join(mod_path, "module.yaml")

        if os.path.isfile(spec_path):
            spec = yaml.load(open(spec_path), Loader=SafeLoader)
            output.extend(spec.get("pip-requirements", []))

    return output

if __name__ == "__main__":
    print(" ".join(get_requirements()))
