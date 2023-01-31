# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
"""Functions for reading/writing Audacity label files."""
from typing import Iterable, List

from .htk import load_htk_label_file, write_htk_label_file

__all__ = ['load_audacity_label_file', 'write_audacity_label_file']


def load_audacity_label_file(fpath, target_labels=None, ignored_labels=None):
    """Load speech segments from Audacity label file.

    If both `target_labels` and `ignore_labels` are unset, then all segments in
    `fpath` will be considered speech segments. If `target_labels` is set, then
    only segments from `fpath` with a label in `target_labels` will be
    returned. If `ignored_labels` is set, then only segments from `fpath`
    with a label *NOT* in `ignore_labels` will be returned.

    Parameters
    ----------
    fpath : pathlib.Path
        Path to file in Audacity label file format.

    target_labels : Iterable[str], optional
        Target labels. All segments in `fpath` with with one of these labels
        will be considered speech segments.
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
    https://manual.audacityteam.org/man/importing_and_exporting_labels.html
    """
    return load_htk_label_file(
        fpath, target_labels=target_labels, ignored_labels=ignored_labels,
        in_sec=True)


def write_audacity_label_file(fpath, segs, rec_dur=None, is_sorted=False,
                              precision=2):
    """Write speech segments to Audacity label file.

    The resulting file will contain alternating speech/non-speech segments.

    Parameters
    ----------
    fpath : pathlib.Path
        Path to file in Audacity label file format.

    segs : Iterable[Segment]
        Speech segments.

    rec_dur : float, optional
        Recording duration in seconds. Used to set boundary of final non-speech
        segment. If None, set to ``segs[-1].offset``.
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
    https://manual.audacityteam.org/man/importing_and_exporting_labels.html
    """
    write_htk_label_file(
        fpath, segs=segs, rec_dur=rec_dur, is_sorted=is_sorted, in_sec=True,
        precision=precision)
