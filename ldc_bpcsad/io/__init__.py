# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for reading/writing various segmentation file formats."""
from .htk import load_htk_label_file, write_htk_label_file

__all__ = ['load_htk_label_file', 'write_htk_label_file']
