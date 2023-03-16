# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    Comment,
    Name,
    Text,
    Keyword,
    Operator,
    Whitespace,
    Punctuation,
)
from sphinx.highlighting import lexers
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

import avm_doc  # noqa

avm_doc.generate_avm_rst()


# This is a very crude lexer but it does the job for now
class TealishLexer(RegexLexer):
    name = "tealish"
    aliases = []
    filenames = ["*.tl"]

    tokens = {
        "root": [
            (r"\s+$", Text),
            (r"\s*#.*$", Comment.Single),
            (
                r"(\s*)(if)(\s*)(.*)(:)$",
                bygroups(Whitespace, Keyword, Whitespace, Text, Keyword),
            ),
            (r"(\s*)(elif)(\s*)(.*)(:)$", bygroups(Text, Keyword, Text, Text, Keyword)),
            (r"(\s*)(else:)$", bygroups(Text, Keyword)),
            (r"(\s*)(end)$", bygroups(Text, Keyword)),
            (
                r"(\s*)(switch)(\s*)(.*)(:)$",
                bygroups(Whitespace, Keyword, Whitespace, Text, Keyword),
            ),
            (
                r"(\s*)(block)(\s*)(.*)(:)$",
                bygroups(Whitespace, Keyword, Whitespace, Name.Class, Keyword),
            ),
            (
                r"(\s*)(struct)(\s*)(.*)(:)$",
                bygroups(Whitespace, Keyword, Whitespace, Name.Class, Keyword),
            ),
            (r"(\s*)(inner_txn:)$", bygroups(Whitespace, Keyword)),
            (r"(\s*)(teal:)$", bygroups(Whitespace, Keyword)),
            (
                r"(\s*)(func)(\s)([^\s]*?)(\()(.*)(\))(.*)(:)$",
                bygroups(
                    Whitespace,
                    Keyword,
                    Whitespace,
                    Name.Function,
                    Punctuation,
                    Text,
                    Punctuation,
                    Text,
                    Keyword,
                ),
            ),
            (
                r"(\s*)(return)(\s*)(.*)$",
                bygroups(Whitespace, Keyword, Whitespace, Text),
            ),
            (r"(\s*)(.+?:)(\s)(.+?)$", bygroups(Whitespace, Keyword, Whitespace, Text)),
            (
                r"(\s*)(.+?)(\s)(\=)(\s)(.+?)$",
                bygroups(
                    Whitespace, Name.Variable, Whitespace, Operator, Whitespace, Text
                ),
            ),
            (
                r"(\s*)([^\s]*?)(\s)([^\s]*?)$",
                bygroups(Whitespace, Keyword.Type, Whitespace, Name.Variable),
            ),
            (
                r"(\s*)([^\s]*?)(\s)([^\s]*?)(\s)(\=)(\s)(.+?)$",
                bygroups(
                    Whitespace,
                    Keyword.Type,
                    Whitespace,
                    Name.Variable,
                    Whitespace,
                    Operator,
                    Whitespace,
                    Text,
                ),
            ),
            (
                r"(\s*)([^\s]*?)(\()(.*?)(\))$",
                bygroups(Text, Name.Function, Punctuation, Text, Punctuation),
            ),
        ]
    }


lexers["tealish"] = TealishLexer()

pygments_style = "solarized-dark"

# highlight_language = 'tealish'

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

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
