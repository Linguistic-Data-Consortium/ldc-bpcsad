# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for reading/writing RTTM files."""
from typing import Iterable, List

from ..segment import Segment

__all__ = ['load_rttm_file', 'write_rttm_file']


def load_rttm_file(fpath):
    """Load speech segments from Rich Transcription Time Marked (RTTM) file.

    **NOTE** that this will load **ALL** segments in the file, regardless of
    recording, channel, or speaker.

    Parameters
    ----------
    fpath : pathlib.Path
        Path to file in RTTM file format.

    Returns
    -------
    List[Segment]
        Speech segments.

    References
    ----------
    .. [1] NIST. (2009). "The 2009 (RT-09) Rich Transcription Meeting Recognition Evaluation Plan." `[link] <https://web.archive.org/web/20100606092041if_/http://www.itl.nist.gov/iad/mig/tests/rt/2009/docs/rt09-meeting-eval-plan-v2.pdf>`_
    """
    with open(fpath, 'r', encoding='utf-8') as f:
        segs = []
        for line in f:
            fields = line.strip().split()
            onset = float(fields[3])
            dur = float(fields[4])
            segs.append(Segment(onset, onset + dur))
    return segs


def write_rttm_file(rttm_path, segs, file_id, channel=1, is_sorted=False,
                    precision=2):
    """Write speech segments to Rich Transcription Time Marked (RTTM) file.

    Parameters
    ----------
    rttm_path : pathlib.Path
        Path to file in RTTM format.

    segs : Iterable[Segment]
        Speech segments.

    file_id : str
        File ID to output with segment. Typically, basename of the audio file
        the segment is on.

    channel : int, optional
        Channel segment is on in audio file (1 indexed).
        (Default: 1)

    is_sorted : bool, optional
        If True, treat `segs` as already sorted. Otherwise, sort before
        writing.
        (Default: False)

    precision : int, optional
        Output will be truncated to `precision` decimal places.
        (Default: 2)

    References
    ----------
    .. [1] NIST. (2009). "The 2009 (RT-09) Rich Transcription Meeting Recognition Evaluation Plan." `[link] <https://web.archive.org/web/20100606092041if_/http://www.itl.nist.gov/iad/mig/tests/rt/2009/docs/rt09-meeting-eval-plan-v2.pdf>`_
    """
    if not (isinstance(channel, int) and 1 <= channel):
        raise ValueError('Channel must be an integer >= 1.')
    def _f2s(x, precision):
        return f'{x:.{precision}f}'
    if not is_sorted:
        segs = sorted(segs)
    with open(rttm_path, 'w', encoding='utf-8') as f:
        for seg in segs:
            onset = round(seg.onset, precision)
            offset = round(seg.offset, precision)
            dur = offset - onset
            onset = _f2s(onset, precision)
            dur = _f2s(dur, precision)
            f.write(f'SPEAKER {file_id} {channel} {onset} {dur} <NA> <NA> '
                    f'speaker <NA> <NA>\n')
