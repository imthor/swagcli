# pylint: disable=missing-module-docstring
from setuptools import setup

setup(
    name="swagcli",
    version="0.1",
    description="Get easy click cli for your api using swagger config",
    author="imthor",
    install_requires=["anytree", "click", "requests"],
    license="MIT",
    packages=["swagcli"],
)
