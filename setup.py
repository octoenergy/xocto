from codecs import open
from os import path

from setuptools import setup


REPO_ROOT = path.abspath(path.dirname(__file__))

VERSION = "4.6.0"

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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    packages=["xocto", "xocto.events", "xocto.storage"],
    package_data={"xocto": ["py.typed"]},
    zip_safe=False,
    install_requires=[
        "ddtrace>=1.9.0",
        "duckdb>=0.9.0",
        "django>=4.0",
        "openpyxl>=3.1.0",
        "pact-python>=1.6.0",
        "pandas>=1.5.3",
        "pyarrow>=11.0.0",
        "python-dateutil>=2.8.2",
        "python-magic>=0.4.27",
        "pytz",
        "structlog>=20.2.0",
        "xlrd>=2.0.1",
    ],
    extras_require={
        "dev": [
            "black==22.12.0",
            "boto3==1.26.53",
            "botocore==1.29.53",
            "mypy-boto3-s3==1.26.0.post1",
            "mypy==0.991",
            "numpy==1.22.2",
            "pre-commit>=3.2.0",
            "pyarrow-stubs==10.0.1.6",
            "ruff==0.0.292",
            "twine==4.0.2",
            "types-openpyxl==3.0.4.5",
            "types-python-dateutil==2.8.19.6",
            "types-pytz==2022.7.1.0",
            "types-requests==2.28.11.8",
            "wheel==0.38.4",
        ],
        "test": [
            "ruff==0.0.292",
            "hypothesis==6.62.1",
            "moto[s3,sqs]==4.1",
            "pytest-django==4.5.2",
            "pytest-mock==3.10.0",
            "pytest==7.2.1",
            "time-machine==2.9.0",
        ],
    },
    project_urls={
        "Documentation": "https://xocto.readthedocs.io",
        "Changelog": "https://github.com/octoenergy/xocto/blob/main/CHANGELOG.md",
        "Issues": "https://github.com/octoenergy/xocto/issues",
    },
)
