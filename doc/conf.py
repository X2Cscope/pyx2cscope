"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html

-- Project information -----------------------------------------------------
https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
"""
import os
import sys

import pyx2cscope

project = "pyX2Cscope"
copyright = "2024, Yash Agarwal, Edras Pacola, Mark Wendler, Christof Baumgartner"
author = "Yash Agarwal, Edras Pacola, Mark Wendler, Christof Baumgartner"
html_favicon = "images/pyx2cscope.ico"

# The short X.Y version.
version = pyx2cscope.__version__.split("-", maxsplit=1)[0]
release = pyx2cscope.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

sys.path.insert(0, os.path.abspath("../pyx2cscope"))

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
    "sphinx.ext.autosummary",
    "autoapi.extension",
]

autoapi_dirs = ["../pyx2cscope"]
autoapi_ignore = [
    "*/examples/*",
    "*/gui/*",  # For now, we ignore this, TODO: fix this
]

suppress_warnings = ["autoapi.python_import_resolution"]  # Suppress warnings about unresolved imports TODO: fix this

nitpick_ignore = [
    ("py:class", "numbers.Number"),
    ("py:class", "mchplnet.lnet"),  # For now, we ignore this, TODO: fix this
    (
        "py:class",
        "pyx2cscope.variable.variable.LNet",
    ),  # For now, we ignore this, TODO: fix this
    ("py:obj", "abc.ABC"),  # For now, we ignore this, TODO: fix this
    (
        "py:class",
        "mchplnet.services.scope.ScopeChannel",
    ),  # For now, we ignore this, TODO: fix this
    (
        "py:class",
        "mchplnet.interfaces.abstract_interface.InterfaceABC",
    ),  # For now, we ignore this, TODO: fix this
]

graphviz_output_format = "png"  # 'svg' is also possible

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
