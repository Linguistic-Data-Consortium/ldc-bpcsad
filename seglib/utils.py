# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Miscellaneous utility functions related to audio and segmentation."""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import os
import subprocess

__all__ = ['concat_segs', 'convert_to_wav', 'elim_short_segs', 'get_dur',
           'merge_segs']


def get_dur(af):
    """Return duration of audio file.

    Parameters
    ----------
    af : str
        Path to audio file. May be in any format understood by SoX or ffmpeg.

    Returns
    -------
    dur : float
        Duration of audio file (seconds).
    """
    try:
        cmd = ['soxi', '-D', af]
        with open(os.devnull, 'wb') as f:
            dur = float(subprocess.check_output(cmd, stderr=f))
        return dur
    except subprocess.CalledProcessError:
        pass
    try:
        cmd = ['ffprobe',
               '-i', af,
               '-show_entries', 'format=duration',
               '-v', 'quiet',
               '-of', 'csv=p=0']
        with open(os.devnull, 'wb') as f:
            dur = float(subprocess.check_output(cmd, stderr=f))
        return dur
    except subprocess.CalledProcessError:
        raise IOError('Error opening: %s' % af)


def convert_to_wav(wf, af, channel=1, start=0, end=None):
    """Convert audio file to 16 kHz, 16 bit WAV file.

    Parameters
    ----------
    wf : str
       Output WAV file.

    af : str
        Path to audio file containing the recording. May be in any format
        understood by SoX or ffmpeg.

    target_sr : int, optional
        Target sample rate (Hz), to which recording will be resampled using
        SoX. If None, do not resample.
        (Default: Recording sample rate.)

    channel : int, optional
        Channel to extract (1-indexed).
        (Default: 1)

    start : float, optional
        Time (seconds) of center of first frame.
        (Default: 0)

    end : float, optional
        Time (seconds) of center of last frame.
        (Default: Duration of recording.)
    """
    if end is None:
        end = get_dur(af)

    # Resample and load into array.
    try:
        cmd = ['sox', af,
               '-b', '16', # Make 16-bit
               '-e', 'signed-integer', # And linear PCM
               '-t', 'wav',
               wf,
               'remix', str(channel), # Extract single channel.
               'trim', str(start), '=%s' % end,
               'rate', '16000',
               ]
        with open(os.devnull, 'wb') as f:
            raw = subprocess.check_output(cmd, stderr=f)
        return
    except subprocess.CalledProcessError:
        pass
    try:
        cmd = ['ffmpeg',  '-i', af, wf]
        with open(os.devnull, 'wb') as f:
            raw = subprocess.check_output(cmd, stderr=f)
    except subprocess.CalledProcessError:
        raise IOError('Error opening: %s' % af)


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
