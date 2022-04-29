from codecs import open
from os import path

from setuptools import setup

REPO_ROOT = path.abspath(path.dirname(__file__))

VERSION = "1.5"

with open(path.join(REPO_ROOT, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="xocto",
    version=VERSION,
    description="Kraken Technologies Python service utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/octoenergy/xocto",
    author="Kraken Technologies",
    author_email="talent@octopus.energy",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["xocto", "xocto.events"],
    package_data={"xocto": ["py.typed"]},
    zip_safe=False,
    install_requires=[
        "pytz==2022.1",
        "django==3.2.13",
        "structlog==20.2.0",
        "python-dateutil==2.8.2",
    ],
    extras_require={
        "dev": ["wheel==0.29.0", "twine==1.8.1", "black==22.3.0", "isort==5.10.1"],
        "test": [
            "flake8==4.0.1",
            "pytest==7.0.1",
            "pytest-django==4.5.2",
            "hypothesis==5.49.0",
            "time-machine==2.6.0",
        ],
    },
)
