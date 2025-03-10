# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import sphinx_rtd_theme

for x in os.walk("../src"):
    sys.path.insert(0, x[0])

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("../src/gana/*"))
sys.path.insert(0, os.path.abspath("../"))
sys.path.insert(0, os.path.abspath("../../"))

sys.setrecursionlimit(10000)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'gana'
copyright = '2025, Rahul Kakodkar'
author = 'Rahul Kakodkar'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_mdinclude',
    'sphinx_rtd_theme',
    'sphinx.ext.napoleon',
    'nbsphinx',
    'sphinx.ext.mathjax',
]

myst_enable_extensions = ["amsmath"]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
html_logo = "gana-logo.png"
source_suffix = [".rst", ".md"]
nbsphinx_execute = 'never'
