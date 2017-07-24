# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""TODO"""
from __future__ import unicode_literals

__all__ = ['read_label_file', 'write_label_file']


def read_label_file(lf, in_sec=True, enc='utf-8'):
    """Read segmentation from HTK label file.

    Parameters
    ----------
    lf : str
        Path to label file.

    in_sec : bool, optional
        If True then onsets/offsets in ``lf`` are assumed to be in seconds. If
        False they are assumed to be in HTK 100 ns units.
        (Default: True)

    enc : str, optional
        Character encoding of ``lf``.
        (Default: 'utf-8')

    Returns
    -------
    segs : list of tuple
        List of segments, each expressed as a tuple
        (``onset``, ``offset``, ``label``), where ``onset`` and ``offset`` are
        the onset and offset of the segment in seconds relative to the start
        of the recording.
    """
    with open(lf, 'rb') as f:
        segs = [line.decode(enc).strip().split()[:3] for line in f]

    for seg in segs:
        seg[0] = float(seg[0])
        seg[1] = float(seg[1])
        if not in_sec:
            seg[0] = htk_units_2_seconds(seg[0])
            seg[1] = htk_units_2_seconds(seg[1])

    return segs


def write_label_file(lf, segs, in_sec=True, enc='utf-8'):
    """Write segmentation to HTK label file.

    Parameters
    ----------
    lf : str
        Path to label file.

    segs : list of tuple
        List of segments, each expressed as a tuple
        (``onset``, ``offset``, ``label``), where ``onset`` and ``offset`` are
        the onset and offset of the segment in seconds relative to the start
        of the recording.

    in_sec : bool, optional
        If True then write onsets and offsets in terms of seconds. If False
        then write in terms of HTK 100 ns units.
        (Default: True)

    enc : str, optional
        Character encoding of ``lf``.
        (Default: 'utf-8')
    """
    with open(lf, 'wb') as f:
        for onset, offset, label in segs:
            if not in_sec:
                onset = seconds_2_htk_units(onset)
                offset = seconds_2_htk_units(offset)
                line = '%d %d %s\n' % (onset, offset, label)
            else:
                line = '%.2f %.2f %s\n' % (onset, offset, label)
            f.write(line.encode(enc))


def htk_units_2_seconds(t):
    """Convert from 100 ns units to seconds.
    """
    return t*10.**-7


def seconds_2_htk_units(t):
    """Convert from seconds to 100 ns units, rounded down to nearest integer.
    """
    return int(t*10**7)
