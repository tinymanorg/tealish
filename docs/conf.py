# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
from datetime import datetime

project = "Tealish"
copyright = f"{datetime.now().year}, Tinyman"
author = "Tinyman"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = [
    "_static",
    # "../img"
]


# https://alabaster.readthedocs.io/en/latest/customization.html
# html_logo = ""
html_theme_options = {
    "logo_name": "Tealish",
    # "logo": "",
    "description": "A readable language for Algorand",
    "github_user": "tinymanorg",
    "github_repo": "tealish",
    "fixed_sidebar": True,
    "github_button": True,
    "github_type": "star",
}
