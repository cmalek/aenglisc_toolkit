# Copyright (C) 2026 Chris Malek.
# ruff: noqa: INP001
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
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import sphinx_rtd_theme  # noqa: F401

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

sys.path.insert(0, os.path.abspath("../.."))  # noqa: PTH100
YEAR = datetime.now(tz=ZoneInfo("UTC")).year

# -- Project information -----------------------------------------------------

# the master toctree document
master_doc: str = "index"

project: str = "Ænglisc Toolkit"
copyright: str = f"{YEAR}, Chris Malek"  # noqa: A001
author: str = "Chris Malek"

# The full version, including alpha/beta/rc tags
release: str = "1.0.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions: list[str] = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.images",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
]

source_suffix: str = ".rst"

# Add any paths that contain templates here, relative to this directory.
templates_path: list[str] = ["_templates"]

autodoc_member_order: str = "groupwise"

# Pydantic signatures include runtime constraint metadata that is not public API.
autodoc_typehints: str = "none"

# Make Sphinx not expand all our Type Aliases
autodoc_type_aliases: dict[str, str] = {}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: list[str] = ["_build"]

# the locations and names of other projects that should be linked to this one
intersphinx_mapping: dict[str, tuple[str, str | None]] = {
    "python": ("https://docs.python.org/3", None),
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme: str = "sphinx_rtd_theme"
html_show_sourcelink: bool = False
html_show_sphinx: bool = False
html_show_copyright: bool = True
html_theme_options: dict[str, Any] = {"collapse_navigation": False}
