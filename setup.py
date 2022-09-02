#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    #Package.
    packages=find_packages(exclude=['tests', '__pycache__']),
    entry_points={'console_scripts' : ['ldc-bpcsad=ldc_bpcsad.cli:main',],},
    # TODO: Determine required versions.
    install_requires=[
        'numpy',
        'scipy',
        'sortedcontainers',
        'soundfile',
        'tqdm'],
    extras_require={
        'testing' : ['pytest',
                     'pytest-mock'],
        'doc' : ['Sphinx',
                 'sphinx_rtd_theme']
        },
    # Versioning.
#    version=versioneer.get_version(),
#    cmdclass=versioneer.get_cmdclass(),
    # PyPI.
    name='ldc_bpcsad',
    description='A broad phonetic class based speech activity detector.',
    author='Neville Ryant',
    author_email='nryant@ldc.upenn.edu')
