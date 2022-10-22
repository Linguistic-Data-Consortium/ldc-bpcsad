#!/usr/bin/env python
# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
from setuptools import setup, find_packages

import versioneer

setup(
    #Package.
    packages=find_packages(exclude=['tests', '__pycache__']),
    entry_points={'console_scripts' : ['ldc-bpcsad=ldc_bpcsad.cli:main',],},
    package_data={'ldc_bpcsad' : ['model/*']},
    include_package_date=True,
    # Requirements.
    python_requires='>=3.7',
    install_requires=[
        'numpy>=1.16.5',
        'scipy>=1.7.0',
        'soundfile>=0.10.3',
        'tqdm>=4.38.0'],
    extras_require={
        'testing' : ['pytest',
                     'pytest-mock'],
        'doc' : ['Sphinx',
                 'sphinx-argparse',
                 'sphinxcontrib-bibtex',
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
