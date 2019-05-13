from homecontrol import const

from setuptools import setup, find_namespace_packages

REQUIREMENTS = open("requirements.txt").read().splitlines()

MINIMUM_PYTHON_VERSION = ">="+".".join(map(str, const.MINIMUM_PYTHON_VERSION))

setup(
    name="homecontrol",
    url="https://github.com/lennart-k/HomeControl",
    author="Lennart K",
    description="Another approach to home automation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=("homecontrol", "homecontrol.*")),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    python_requires=MINIMUM_PYTHON_VERSION,
    package_data={
        "": ["*"]
    },
    license="MIT",
    keywords="homecontrol home automation",
    project_urls={
        "GitHub": "https://github.com/lennart-k/HomeControl"
    },
    entry_points={
        "console_scripts": [
            "homecontrol = homecontrol.__main__:main"
        ]
    }
)
