"""Helper to find the pip requirements for a builtin module"""
import os
import pkg_resources
from argparse import ArgumentParser

import homecontrol
from yaml.loader import SafeLoader
import yaml

MODULE_FOLDER = pkg_resources.resource_filename(
    homecontrol.__name__, "modules")

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-testrepo", action="store_true")
    return parser.parse_args()

def get_requirements(test_repo: bool = False) -> list:
    """
    Lists the pip requirements for the builtin folder modules
    """
    output = []
    field = "pip-requirements" if not test_repo else "pip-test-requirements"

    for node in os.listdir(MODULE_FOLDER):
        if node == "__pycache__":
            continue
        mod_path = os.path.join(MODULE_FOLDER, node)
        spec_path = os.path.join(mod_path, "module.yaml")

        if os.path.isfile(spec_path):
            spec = yaml.load(open(spec_path), Loader=SafeLoader)
            output.extend(spec.get(field, []))

    return output

if __name__ == "__main__":
    args = parse_args()
    print(" ".join(get_requirements(args.testrepo)))
