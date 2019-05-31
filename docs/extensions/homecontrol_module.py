"""
This extension currently copies docs from the homecontrol package
to _homecontrol so that module documentations are automatically included
"""

import shutil
import os
import pkg_resources
from sphinx.application import Sphinx


def setup(app: Sphinx) -> None:
    """Setup the extension"""
    module_path = pkg_resources.resource_filename("homecontrol", "modules")

    if os.path.isdir("_homecontrol/modules"):
        shutil.rmtree("_homecontrol/modules")

    os.makedirs("_homecontrol/modules")

    for module in os.listdir(module_path):
        docs_path = os.path.join(module_path, module, "docs.rst")
        if os.path.isfile(docs_path):
            shutil.copyfile(docs_path, f"_homecontrol/modules/{module}.rst")

        docs_path = os.path.join(module_path, module, "docs.md")
        if os.path.isfile(docs_path):
            shutil.copyfile(docs_path, f"_homecontrol/modules/{module}.md")
