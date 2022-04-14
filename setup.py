from codecs import open
from os import path

from setuptools import find_packages, setup

REPO_ROOT = path.abspath(path.dirname(__file__))

VERSION = "1.4"

with open(path.join(REPO_ROOT, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="xocto",
    version=VERSION,
    description="Octopus Energy Python service utilities",
    long_description=long_description,
    url="https://github.com/octoenergy/xocto",
    author="Octopus Energy",
    author_email="talent@octopus.energy",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "pytz==2022.1",
        "django==3.2.13",
        "structlog==20.2.0",
        "python-dateutil==2.8.2",
    ],
    extras_require={
        "dev": ["wheel==0.29.0", "twine==1.8.1", "black==22.3.0", "isort==4.3.21"],
        "test": [
            "flake8==3.0.4",
            "pytest==3.0.2",
            "pytest-django==3.0.0",
            "pandas==1.0.5",
            "hypothesis==5.49.0",
        ],
    },
)
