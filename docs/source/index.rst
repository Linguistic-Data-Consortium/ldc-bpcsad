.. ldc_bpcsad documentation master file, created by
   sphinx-quickstart on Mon Sep 12 15:52:41 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#################################################
LDC Broad Phonetic Class Speech Activity Detector
#################################################

`ldc-bpcsad` is a speech activity detector (SAD) developed at `Linguistic Data Consortium (LDC) <https://www.ldc.upenn.edu/>`_ based on recognition of broad phonetic classes.


Installation
============

To install into the current Python environment:

  .. code-block:: console
		
    git clone https://github.com/Linguistic-Data-Consortium/ldc_bpcsad.git
    cd ldc_bpcsad
    pip install .


HTK
---

The SAD engine depends on `HTK <https://htk.eng.cam.ac.uk/>`_ for feature extraction and decoding. To install HTK for Linux:

- `register <https://htk.eng.cam.ac.uk/register.shtml>`_ a username/password
- accept the the license agreement
- download the `latest stable release <https://htk.eng.cam.ac.uk/ftp/software/HTK-3.4.1.tar.gz>`_
- untar:

  .. code-block:: console

    tar -xvf HTK-3.4.1.tar.gz
  
- compile and install:

  .. code-block:: console

    cd htk
    ./configure --without-x --disable-hslab --disable-hlmtools
    make all -j 4
    make install

  
Getting started
===============

.. toctree::
   :maxdepth: 1
      
   model
   cli
   api
   

Citation
========

If you use `ldc-bpcsad` in your research, please use the following citation:

::

  @inproceedings{ldc-bpcsad,
    author = {Neville Ryant},
    title = {Linguistic Data Consortium Broad Phonetic Class Speech Activity Detector (ldc-bpcsad)},
    booktitle = {{Interspeech 2017, 18th Annual Conference of the International Speech Communication Association}},
    year = {2012},
    url = {https://github.com/Linguistic-Data-Consortium/ldc_bpcsad},
  }

   

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
