# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""TODO"""
from __future__ import unicode_literals

__all__ = ['elim_short_segs', 'merge_segs']


def merge_segs(segs):
    """Merge sequences of segments with same label.
    """
    new_segs = []
    while len(segs) > 1:
        curr = segs.pop()
        prev = segs.pop()
        if curr[-1] == prev[-1]:
            new = [prev[0], curr[1], curr[-1]]
            segs.append(new)
        else:
            segs.append(prev)
            new_segs.append(curr)
    new_segs.append(segs.pop())
    new_segs.reverse()
    return new_segs


def elim_short_segs(segs, target_lab='nonspeech', replace_lab='speech',
                    min_dur=0.300):
    """Convert nonspeech segments below specified duration to speech.

    Parameters
    ----------
    segs : list of tuple
        List of segments, each expressed as a tuple
        (``onset``, ``offset``, ``label``), where ``onset`` and ``offset`` are
        the onset and offset of the segment in seconds relative to the start
        of the recording.

    target_lab : str, optional
        Label of segments to filter.
        (Default: 'nonspeech')

    replace_lab : str, optional
        Label to replace segments of type ``target_lab`` which fall below the
        cutoff.
        (Default: 'speech')

    min_dur : float, optional
        Minimum allowed duration (seconds) for segments of type ``target_lab``.
        Segments falling below ``min_dur`` will be remapped to ``replace_lab``.
        Duration cutoff (seconds) below which
        (Default: 0.300)

    Returns
    -------
    new_segs
    """
    for seg in segs:
        onset, offset, label = seg
        dur = offset - onset
        if label == target_lab and dur < min_dur:
            seg[-1] = replace_lab
    return segs
