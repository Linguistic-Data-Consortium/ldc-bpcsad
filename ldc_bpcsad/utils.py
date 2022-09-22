# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Miscellaneous utility functions related to audio and segmentation."""
import dataclasses
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import scipy.signal

__all__ = ['add_dataclass_slots', 'clip', 'resample', 'which']


def resample(x, orig_sr, new_sr):
    """Resample audio from `orig_sr` to `new_sr` Hz.

    Uses polyphase resampling as implemented within :mod:`scipy.signal`.

    Parameters
    ----------
    x : numpy.ndarray, (n_samples,)
        Time series to be resampled.

    orig_sr : int
        Original sample rate (Hz) of `x`.

    new_sr : int
        New sample rate (Hz).

    Returns
    -------
    x_resamp : numpy.ndarray, (n_samples * new_sr / orig_sr,)
        Version of `x` resampled from `orig_sr` Hz to `new_sr` Hz.

    See also
    --------
    scipy.signal.resample_poly
    """
    gcd = np.gcd(orig_sr, new_sr)
    upsample_factor = new_sr // gcd
    downsample_factor = orig_sr // gcd
    return scipy.signal.resample_poly(
        x, upsample_factor, downsample_factor, axis=-1)


def clip(x, lb, ub):
    """Clip `x` to interval [`lb`, `ub`]."""
    if ub <= lb:
        raise ValueError(f'Invalid clipping interval: [{lb}, {ub}].')
    return max(lb, min(x, ub))


def add_dataclass_slots(cls):
    """Add `__slots__` to a data class.

    Notes
    -----
    https://github.com/ericvsmith/dataclasses/blob/master/dataclass_tools.py
    """
    # Need to create a new class, since we can't set __slots__
    #  after a class has been created.

    # Make sure __slots__ isn't already set.
    if '__slots__' in cls.__dict__:
        raise TypeError(f'{cls.__name__} already specifies __slots__')

    # Create a new dict for our new class.
    cls_dict = dict(cls.__dict__)
    field_names = tuple(f.name for f in dataclasses.fields(cls))
    cls_dict['__slots__'] = field_names
    for field_name in field_names:
        # Remove our attributes, if present. They'll still be
        #  available in _MARKER.
        cls_dict.pop(field_name, None)

    # Remove __dict__ itself.
    cls_dict.pop('__dict__', None)
    # And finally create the class.
    qualname = getattr(cls, '__qualname__', None)
    cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
    if qualname is not None:
        cls.__qualname__ = qualname
    return cls


def which(program, search_dirs=None):
    """Returns path to excutable `program`.

    If `program` is not found on the user's PATH, returns ``None``.

    Parameters
    ----------
    program : str
        Name of program to search for.

    search_dirs : Iterable[pathlib.Path], optional
        List of additional directories to search. These directories will be
        searched in order **BEFORE** the user's PATH.
        (Default: None)
    """
    def is_exe(fpath):
        return fpath.is_file() and os.access(fpath, os.X_OK)
    program = Path(program)
    if search_dirs is None:
        search_dirs = []
    search_dirs = list(search_dirs)
    search_dirs += os.environ['PATH'].split(os.pathsep)
    if is_exe(program):
        return program
    for dirpath in search_dirs:
        fpath = Path(dirpath, program)
        if is_exe(fpath):
            return fpath
    return None
