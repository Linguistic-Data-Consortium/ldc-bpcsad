#!/usr/bin/env python
# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
from setuptools import setup, find_packages

import versioneer

setup(
    #Package.
    package_dir = {'' : 'src'},
    packages=find_packages(where='src', exclude=['tests', '__pycache__']),
    entry_points={'console_scripts' : ['ldc-bpcsad=ldc_bpcsad.cli:main',],},
    package_data={'ldc_bpcsad' : ['model/*']},
    include_package_data=True,
    # Requirements.
    python_requires='>=3.7',
    install_requires=[
        'numpy>=1.16.5',
        'scipy>=1.7.0',
        'soundfile>=0.11.0',
        'tqdm>=4.38.0'],
    extras_require={
        'testing' : ['pytest',
                     'pytest-mock'],
        'doc' : ['Sphinx',
                 'sphinx-argparse',
                 'sphinxcontrib-bibtex',
                 'sphinx-tabs',
                 'sphinx_rtd_theme',
                 'ipython']
        },
    # Versioning.
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    # PyPI.
    name='ldc-bpcsad',
    description='A broad phonetic class based speech activity detector.',
    author='Neville Ryant',
    author_email='nryant@ldc.upenn.edu')
