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
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

import ldc_bpcsad


##############################################################################
# Project information.
##############################################################################
project = 'ldc-bpcsad'
copyright = '2012-2022, Trustees of the University of Pennsylvania'
author = 'Neville Ryant'
version = ldc_bpcsad.__version__.split('+')[0]
release = ldc_bpcsad.__version__


##############################################################################
# Config
##############################################################################
# Sphinx extensions.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinxcontrib.bibtex',
    'sphinx_tabs.tabs',
    'sphinxarg.ext',
    'IPython.sphinxext.ipython_directive',
    'sphinx_rtd_theme']


# Napoleon settings.
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True


# Intersphinx.
intersphinx_mapping = {
    'python' : ('https://docs.python.org/3', None),
    'numpy' : ('http://docs.scipy.org/doc/numpy', None),
    'scipy' : ('https://docs.scipy.org/doc/scipy/', None),
    'soundfile' : ('https://pysoundfile.readthedocs.io/en/latest', None),
    'sf' : ('https://pysoundfile.readthedocs.io/en/latest', None),
}


# Bibtex.
bibtex_bibfiles = ['refs.bib']
bibtex_default_style = 'plain'


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
import sphinx_rtd_theme
html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_theme_options = {'display_version': True}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named 'default.css' will overwrite the builtin 'default.css'.
html_static_path = ['_static']
