# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from datetime import datetime


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
copyright = str(datetime.now().year)
author = 'Rahul Kakodkar'
release = '1.0.2'


master_doc = 'index'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


extensions = [
    # Allows executing and rendering Jupyter notebooks using MyST-NB
    # Example:
    # .. jupyter-execute::
    #    print("Hello from a notebook cell")
    "myst_nb",
    # Automatically documents Python modules from docstrings
    # Example: .. automodule:: my_package.mymodule
    "sphinx.ext.autodoc",
    # Allows cross-referencing objects in other projects
    # Example: :ref:`python:os.path` (links to Python stdlib docs)
    "sphinx.ext.intersphinx",
    # Adds links to highlighted source code for documented Python objects
    # Example: [source] links next to classes/functions
    "sphinx.ext.viewcode",
    # Generates summary tables for modules/classes/functions
    # Often used with autosummary_generate=True in conf.py
    "sphinx.ext.autosummary",
    # Adds a "copy" button to code blocks for easy copy-paste
    "sphinx_copybutton",
    # Enables Thebe live code cells in the docs
    # Example: .. jupyter-execute:: (cells become live in HTML)
    "sphinx_thebe",
    # Adds collapsible toggle buttons for content (like details/summary)
    # Example:
    # .. toggle::
    #    Hidden content here
    "sphinx_togglebutton",
    # Add support for bibliographies and citations using .bib files
    # Example usage: :cite:`doe2020`
    # "sphinxcontrib.bibtex",
    # Include TODO notes in your docs without breaking the build
    # Example: .. todo:: Add more examples for the API
    "sphinx.ext.todo",
    # Provides design components like cards, grids, buttons, alerts
    # Example: .. card:: This is a card with some text.
    "sphinx_design",
    # Automatically include and display example scripts or notebooks
    # Example: .. example-code:: examples/example_script.py
    "sphinx_examples",
    # Adds tabbed content for side-by-side examples
    # Example:
    # .. tabs::
    #    .. tab:: Python
    #       print("Hello World")
    #    .. tab:: Bash
    #       echo "Hello World"
    "sphinx_tabs.tabs",
    # Adds Open Graph metadata for social sharing (Twitter, LinkedIn, etc.)
    # Example config:
    # ogp_site_url = "https://mydocs.example.com/"
    # ogp_image = "https://mydocs.example.com/logo.png"
    "sphinxext.opengraph",
]

myst_enable_extensions = [
    # Support for LaTeX math environments like \begin{equation}...\end{equation}
    "amsmath",
    # Enable definition lists (key : value syntax)
    # Example:
    # Term
    #   Definition
    "deflist",
    # Render admonitions (notes, warnings, tips) in HTML
    # Example: !!! note "Tip"
    "html_admonition",
    # Enable images in HTML output with extended Markdown syntax
    # Example: ![alt text](image.png)
    "html_image",
    # Automatically convert URLs into links
    # "linkify",
    # Support $...$ inline math and $$...$$ display math
    "dollarmath",
    # Support colon-fenced code blocks
    # Example:
    # :::python
    # print("Hello")
    "colon_fence",
    # Improve quotation marks in rendered HTML (smart quotes)
    "smartquotes",
    # Enable text replacements, like (C) → ©
    "replacements",
    # Enable substitution syntax for custom placeholders
    # Example: {substitution_name}
    "substitution",
]

add_module_names = False

autosummary_context = {
    "skip_module_names": True,
}


templates_path = ['_templates']

exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'jupyter_execute',
    '**.ipynb_checkpoints',
]

autosummary_generate = True
autosummary_imported_members = True
autodoc_inherit_docstrings = True
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'inherited-members': True,
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_logo = "_static/ganalogo.jpg"

html_title = "Gana"
source_suffix = {".rst": 'restructuredtext', ".md": 'markdown', ".ipynb": 'myst-nb'}
html_copy_source = True
html_last_updated_fmt = ""
# html_sidebars = {
#     "reference/blog/*": [
#         "navbar-logo.html",
#         "search-field.html",
#         "sbt-sidebar-nav.html",
#     ]
# }
# toc_object_entries_show_parents = "hide"


suppress_warnings = [
    "ref.python",  # suppress all ambiguous cross-reference warnings in Python domain
]
html_theme_options = {
    "path_to_docs": "docs",
    "repository_url": "https://github.com/cacodcar/gana",
    "repository_branch": "main",
    "use_edit_page_button": True,
    "use_source_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
    "use_download_button": True,
    # "use_sidenotes": True,
    # "show_toc_level": 4,
    # "announcement": (
    #     "Put Announcement Here. "
    # ),
    "logo": {
        "image_dark": "_static/ganalogo.jpg",
        # "text": html_title,  # Uncomment to try text with logo
    },
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/cacodcar/gana",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/gana/",
            "icon": "https://img.shields.io/pypi/dw/gana",
            "type": "url",
        },
    ],
    "launch_buttons": {
        "thebe": True,
        "binderhub_url": "https://mybinder.org",
        "notebook_interface": "classic",  # or "jupyterlab"
        "binder_branch": "main",
        "path_to_docs": "docs/",
        # "colab_url": "https://colab.research.google.com/",
        # "deepnote_url": "https://deepnote.com",
    },
}
nb_execution_mode = "off"

# bibtex_bibfiles = ["refs.bib", "frameworks.bib"]
# bibtex_default_style = "unsrt"
autodoc_member_order = 'bysource'
