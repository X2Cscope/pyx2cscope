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
copyright = "2024, Microchip Technology Inc"
author = "Yash Agarwal, Edras Pacola, Mark Wendler, Christoph Baumgartner"
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
    "sphinx.ext.intersphinx",
    "autoapi.extension",
]

autoapi_dirs = ["../pyx2cscope"]
autoapi_ignore = [
    "*/examples/*",
    "*/gui/*",  # For now, we ignore this
]

suppress_warnings = [
     "autoapi.python_import_resolution"
]  # Suppress warnings about unresolved imports

nitpick_ignore = [
    ("py:class", "pyx2cscope.gui"),
    ("py:class", "mchplnet.lnet"),
    ("py:class", "mchplnet.lnet.LNet"),
    ("py:class", "mchplnet.services.scope.ScopeChannel"),
    ("py:class", "mchplnet.interfaces.factory.InterfaceType"),
    ("py:class", "mchplnet.interfaces.abstract_interface.Interface"),
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

graphviz_output_format = "png"  # 'svg' is also possible

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"

html_theme_options = {
    'navigation_depth': 4,
}