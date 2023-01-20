from codecs import open
from os import path

from setuptools import setup

REPO_ROOT = path.abspath(path.dirname(__file__))

VERSION = "2.2.2"

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
    packages=["xocto", "xocto.events", "xocto.storage"],
    package_data={"xocto": ["py.typed"]},
    zip_safe=False,
    install_requires=[
        "pytz",
        "django>=3.2,<5.0",
        "structlog>=20.2.0",
        "python-dateutil>=2.8.2",
        "pact-python>=1.6.0",
    ],
    extras_require={
        "dev": [
            "wheel==0.38.4",
            "twine==4.0.2",
            "black==22.12.0",
            "isort==5.11.4",
            "boto3==1.26.53",
            "botocore==1.29.53",
            "mypy-boto3-s3==1.26.0.post1",
            "openpyxl==3.0.10",
            "pandas==1.5.3",
            "python-magic==0.4.27",
            "xlrd==2.0.1",
        ],
        "test": [
            "flake8==6.0.0",
            "pytest==7.2.1",
            "pytest-django==4.5.2",
            "hypothesis==6.62.1",
            "time-machine==2.9.0",
            "moto[s3,sqs]==4.1",
            "pytest-mock==3.10.0",
        ],
    },
)
