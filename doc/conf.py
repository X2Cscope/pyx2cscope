# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pyX2Cscope"
copyright = "2024, Yash Agarwal, Edras Pacola, Mark Wendler, Christof Baumgartner"
author = "Yash Agarwal, Edras Pacola, Mark Wendler, Christof Baumgartner"

import pyx2cscope  # pylint: disable=wrong-import-position

# The short X.Y version.
version = pyx2cscope.__version__.split("-", maxsplit=1)[0]
release = pyx2cscope.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os
import sys

sys.path.insert(0, os.path.abspath("../pyx2cscope"))

extensions = [  "myst_parser", 
                "sphinx.ext.autodoc",
                "sphinx.ext.extlinks",
                "sphinx.ext.coverage",
                "sphinx.ext.viewcode",
                "sphinx.ext.graphviz",]

graphviz_output_format = "png"  # 'svg' is also possible

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
