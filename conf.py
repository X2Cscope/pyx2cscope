# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pyx2cscope"
copyright = "2023, Yash Agarwal"
author = "Yash Agarwal"
release = "0.0.5"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_logo = "https://raw.githubusercontent.com/X2Cscope/pyx2cscope/feat-faster-monitoring/pyx2cscope/gui/img/pyx2cscope.jpg"
# The theme to use for HTML and HTML Help pages.
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
