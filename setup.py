"""Setup script to install HomeControl as a package"""

from setuptools import find_namespace_packages, setup
from setuptools.command.develop import develop

from homecontrol import const

MODULE_REQUIREMENTS = []
# Try to extract pip requirements from modules
# Only works if PyYAML is already installed
try:
    from homecontrol.scripts.module_requirements import get_requirements
    MODULE_REQUIREMENTS = get_requirements()
except ModuleNotFoundError:
    pass

REQUIREMENTS = open("requirements.txt").read().splitlines()
REQUIREMENTS_DEV = open("requirements_dev.txt").read().splitlines()
MINIMUM_PYTHON_VERSION = ">=" + \
    ".".join(map(str, const.MINIMUM_PYTHON_VERSION))


class DevelopCommand(develop):
    """"Custom develop command that also install development requirements"""

    def __init__(self, dist, **kw):
        dist.install_requires.extend(REQUIREMENTS_DEV)
        super().__init__(dist)


setup(
    name="homecontrol",
    version=const.VERSION_STRING,
    url="https://github.com/lennart-k/HomeControl",
    author="Lennart K",
    description="Another approach to home automation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=("homecontrol", "homecontrol.*")),
    include_package_data=True,
    install_requires=REQUIREMENTS + MODULE_REQUIREMENTS,
    cmdclass={
        "develop": DevelopCommand
    },
    python_requires=MINIMUM_PYTHON_VERSION,
    package_data={
        "": ["*"]
    },
    license="MIT",
    keywords="homecontrol home automation",
    project_urls={
        "GitHub": "https://github.com/lennart-k/HomeControl",
        "Docs": "https://homecontrol.readthedocs.io/en/latest/"
    },
    entry_points={
        "console_scripts": [
            "homecontrol = homecontrol.__main__:main",
            "homecli = homecontrol.cli.__main__:main"
        ]
    }
)
