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

html_css_files = [
    "css/typography/fonts.css",
    "css/override.css",
    "css/custom.css",
    "css/util-classes.css",
    "css/code-block.css",
    "css/custom-sidebar.css",
    "css/right-column.css",
    "css/searchbox.css",
    "css/search-results.css",
    "css/rolling-content.css",
    "css/responsive.css",
]

html_js_files = [
    "js/custom.js",
    "js/rolling-text.js",
]

# html_sidebars = {'**': ['localtoc.html', 'relations.html', 'sourcelink.html', 'searchbox.html']}
html_sidebars = {"**": ["custom-sidebar.html"]}


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

html_context = {
    "social_links": [
        {"title": "Github", "link": "https://github.com/tinymanorg/tealish"},
        {"title": "Presentation", "link": "https://youtu.be/R9oKjwSYuXM"},
        {
            "title": "Discord",
            "link": "https://discord.com/channels/491256308461207573/1067861991982649404",
        },
        {"title": "Tinyman.org", "link": "https://tinyman.org"},
        {"title": "Twitter", "link": "https://twitter.com/tinymanorg"},
        {"title": "Reddit", "link": "https://www.reddit.com/r/Tinyman/"},
    ],
}
