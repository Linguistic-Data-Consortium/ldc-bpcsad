# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
"""Functions for reading/writing Praat TextGrids."""
from typing import Iterable, List
from collections import namedtuple

from .base import check_segs
from ..segment import Segment

__all__ = ['load_textgrid_file', 'write_textgrid_file']


def load_textgrid_file(fpath, tier=None, target_labels=None,
                       ignored_labels=None):
    """Load speech segments from Praat TextGrid file.

    If both `target_labels` and `ignore_labels` are unset, then all segments in
    `fpath` on the `tier` IntervalTier will be considered speech segments.
    If `target_labels` is set, then only segments from `fpath` with a label in
    `target_labels` will be returned. If `ignored_labels` is set, then only
    segments from `fpath`

    Parameters
    ----------
    fpath : pathlib.Path
        Path to Praat TextGrid file.

    tier : str, optional
        Name of IntervalTier to load segments from. If None, load **ALL** tiers.
        (Default: None)

    target_labels : Iterable[str], optional
        Target labels. All segments with with one of these labels will be
        considered speech segments.
        (Default: None)

    ignored_labels : Iterable[str], optional
        Labels to ignore. Output will be filtered so that segments with a label
        from this set will be skipped. If ``None``, then no filtering is
        performed.
        (Default: None)

    Returns
    -------
    List[Segment]
        Speech segments.

    Notes
    -----
    https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html
    """
    # TODO: Maybe implement this downstream if ever have a need. But not worth
    # effort otherwise.
    raise NotImplementedError


PraatInterval = namedtuple('PraatInterval', ['onset', 'offset', 'label'])


def write_textgrid_file(fpath, segs, tier='sad', rec_dur=None,
                        is_sorted=False, precision=2):
    """Write speech segments to Praat TextGrid file.

    Parameters
    ----------
    fpath : pathlib.Path
        Path to output TextGrid file.

    segs : Iterable[Segment]
        Speech segments.

    tier : str, optional
        Name of IntervalTier to write segments to.
        (Default: 'sad')

    rec_dur : float, optional
        Recording duration in seconds. Used to set boundary of final non-speech
        segment. If None, set to `segs[-1].offset`.
        (Default: None)

    is_sorted : bool, optional
        If True, treat `segs` as already sorted. Otherwise, sort before
        writing.
        (Default: False)

    precision : int, optional
        Output will be truncated to `precision` decimal places.
        (Default: 2)

    Notes
    -----
    https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html
    """
    segs, rec_dur = check_segs(segs, rec_dur)

    # Write speech/nonspeech segmentation.
    def _f2s(x, precision):
        if not precision:
            return x
        return round(x, precision)
    with open(fpath, 'w', encoding='utf-8') as f:
        # Write file header.
        f.write(
            f'File type = "ooTextFile"\n'
            f'Object class = "TextGrid"\n'
            f'\n'
            f'xmin = 0\n'
            f'xmax = {_f2s(rec_dur, precision)}\n'
            f'tiers? <exists>\n'
            f'size = 1\n'
            f'item []:\n')

        # Figure out how many intervals we have.
        if not is_sorted:
            segs = sorted(segs)
        tmp_segs = [Segment(0, 0)]
        tmp_segs.extend(segs)
        tmp_segs.append(Segment(rec_dur, rec_dur))
        intervals = []
        for curr_seg, seg in zip(tmp_segs[:-1], tmp_segs[1:]):
            gap = curr_seg ^ seg
            if curr_seg:
                intervals.append(PraatInterval(
                    curr_seg.onset, curr_seg.offset, 'speech'))
            if gap:
                intervals.append(PraatInterval(
                    gap.onset, gap.offset, 'non-speech'))

        # Write IntervalTier.
        f.write(
            f'    item [1]:\n'
            f'        class = "IntervalTier"\n'
            f'        name = "{tier}"\n'
            f'        xmin = 0\n'
            f'        xmax = {_f2s(rec_dur, precision)}\n'
            f'        intervals: size = {len(intervals)}\n')
        for n, intrvl in enumerate(intervals, start=1):
            f.write(
                f'        intervals [{n}]:\n'
                f'            xmin = {_f2s(intrvl.onset, precision)}\n'
                f'            xmax = {_f2s(intrvl.offset, precision)}\n'
                f'            text = "{intrvl.label}"\n')
