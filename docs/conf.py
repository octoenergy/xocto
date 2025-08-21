# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import pathlib
import sys
from datetime import datetime

import django

# Use pip-vendored tomli so we can read pyproject.toml
# When we upgrade Python to 3.11 we can use tomllib directly
from pip._vendor import tomli


sys.path.insert(0, os.path.abspath(".."))  # for discovery of project modules
sys.path.insert(0, os.path.abspath("."))  # for discovery of doc_settings.py

os.environ["DJANGO_SETTINGS_MODULE"] = "doc_settings"
django.setup()


# -- Project information -----------------------------------------------------

project = "xocto"
copyright = f"{datetime.now().year}, Kraken Tech"
author = "Kraken Tech"

# Fetch the version from pyproject.toml
path = pathlib.Path(__file__).parent / ".." / "pyproject.toml"
pyproject = tomli.loads(path.read_text())
release = pyproject["project"]["version"]

# -- General configuration ---------------------------------------------------


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {"python": ("https://botocore.readthedocs.io/en/latest/", None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
