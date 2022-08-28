# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Miscellaneous utility functions related to audio and segmentation."""
import numpy as np
import scipy.signal

__all__ = ['concat_segs', 'elim_short_segs', 'merge_segs', 'resample']


def concat_segs(seg_seqs, dur=None):
    """Concatenate multiple segmentations.

    Parameters
    ----------
    seg_seqs : list of list
        List of segmentations.

    dur : float, optional
        Duration of the derived segmentation. If None, will be determined
        automatically.
        (Default: None)

    Returns
    -------
    segs : list of tuple
        List of segments, each expressed as a tuple
        (``onset``, ``offset``, ``label``), where ``onset`` and ``offset`` are
        the onset and offset of the segment in seconds relative to the start
        of the recording.
    """
    rec_onset = 0.0
    segs = []
    for segs_ in seg_seqs:
        for onset, offset, label in segs_:
            segs.append([onset + rec_onset, offset + rec_onset, label])
        rec_onset = segs[-1][1]
    if dur is not None:
        if dur > segs[-1][1]:
            segs[-1][1] = dur
    return segs


def merge_segs(segs):
    """Merge sequences of segments with same label."""
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


def resample(x, orig_sr, new_sr):
    """Resample audio from `orig_sr` to `new_sr` Hz.

    Uses polyphase resampling as implemented within `scipy.signal`.

    Parameters
    ----------
    x : ndarray, (nsamples,)
        Time series to be resampled.

    orig_sr : int
        Original sample rate (Hz) of `x`.

    new_sr : int
        New sample rate (Hz).

    Returns
    -------
    x_resamp : ndarray, (nsamples * new_sr / orig_sr,)
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
