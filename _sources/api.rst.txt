*************
API Reference
*************


Data structures
===============

Data structures used to represent speech segments.

.. currentmodule:: ldc_bpcsad

.. autosummary::
   :toctree: generated/
   :template: class.rst
   :recursive:

   segment.Segment


Decoding
========

Functions and classes used to perform SAD on a waveform.

.. currentmodule:: ldc_bpcsad

.. autosummary::
   :toctree: generated/
   :template: function.rst
   :recursive:

   decode.decode
   
   :template: class.rst

   decode.DecodingError


HTK wrappers
============

Functions wrapping HTK command line tools.


.. currentmodule:: ldc_bpcsad

.. autosummary::
   :toctree: generated/
   :template: function.rst
   :recursive:

   htk.hvite
   htk.write_hmmdefs

   :template: class.rst

   htk.HViteConfig
   htk.HTKError


IO
==

Functions for reading/writing segmentatins to files.

.. currentmodule:: ldc_bpcsad

.. autosummary::
   :toctree: generated/
   :template: function.rst
   :recursive:

   io.load_audacity_label_file
   io.write_audacity_label_file
   io.load_htk_label_file
   io.write_htk_label_file
   io.load_rttm_file
   io.write_rttm_file
   io.write_textgrid_file



Utilities
=========

.. currentmodule:: ldc_bpcsad

.. autosummary::
   :toctree: generated/
   :template: function.rst
   :recursive:

   utils.add_dataclass_slots
   utils.clip
   utils.resample
   utils.which
