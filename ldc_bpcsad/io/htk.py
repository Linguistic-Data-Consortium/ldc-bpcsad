# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for reading/writing HTK label files."""
from ..segment import Segment

__all__ = ['load_htk_label_file', 'write_htk_label_file']


def load_htk_label_file(fpath, target_labels=None, ignored_labels=None,
        in_sec=True):
    """Load speech segments from HTK label file.

    If both `target_labels` and `ignore_labels` are unset, then all segments in
    `fpath` will be considered speech segments. If `target_labels` is set, then
    only segments from `fpath` with a label in `target_labels` will be
    returned. If `ignored_labels` is set, then only segments from `fpath`
    with a label *NOT* in `ignore_labels` will be returned.

    Parameters
    ----------
    fpath : Path
        Path to file in HTK label file format.

    target_labels : iterable of str, optional
        Target labels. All segments in `fpath` with with one of these labels
        will be considered speech segments.
        (Default: None)

    ignored_labels : iterable of str, optional
        Labels to ignore. Output will be filtered so that segments with a label
        from this set will be skipped. If ``None``, then no filtering is
        performed.
        (Default: None)

    in_sec : bool, optional
        If True, interpret onsets/offsets within ``fn`` as measuring seconds.
        Else, interpret as measuring HTK 100 ns units.
        (Default: True)
    """
    if target_labels and ignored_labels:
        raise ValueError('At most one of "target_labels" and "ignored_labels" '
                         'should be set.')
    if target_labels:
        target_labels = set(target_labels)
    if ignored_labels:
        ignored_labels = set(ignored_labels)
    with open(fpath, 'r', encoding='utf-8') as f:
        segs = []
        for line in f:
            onset, offset, label = line.strip().split()[:3]

            # Filter non-target segments.
            if target_labels and label not in target_labels:
                continue
            if ignored_labels and label in ignored_labels:
                continue

            # Convert to seconds.
            onset = float(onset)
            offset = float(offset)
            if not in_sec:
                onset *= 100e-9
                offset *= 100e-9

            segs.append(Segment(onset, offset))

    return segs


def write_htk_label_file(fpath, segs, rec_dur=None, is_sorted=False,
                         in_sec=True, precision=2):
    """Write speech segments to HTK label file.

    The resulting file will contain alternating speech/non-speech segments.

    Parameters
    ----------
    fpath : Path
        Path to file in HTK label file format.

    segs : list of Segment
        Speech segments.

    rec_dur : float, optional
        Recording duration in seconds. Used to set boundary of final non-speech
        segment. If None, set to `segs[-1].offset`.
        (Default: None)

    is_sorted : bool, optional
        If True, treat `segs` as already sorted. Otherwise, sort before
        writing.
        (Default: False)

    in_sec : bool, optional
        If True, write onsets/offsets in seconds. Else, write onsets/offsets in
        HTK 100 ns units.
        (Default: True)

    precision : int, optional
        Output will be truncated to `precision` decimal places.
        (Default: 2)
    """
    max_offset = None
    if segs:
        max_offset = max(seg.offset for seg in segs)

    # Validation to ensure we can output a valid segmentation.
    if not segs and rec_dur is None:
        raise ValueError('if "segs" is empty, "rec_dur" must be set')
    if rec_dur:
        if not rec_dur > 0:
            raise ValueError('"rec_dur" must be positive')
        if segs and rec_dur < max_offset:
            raise ValueError('segments cannot extend past "rec_dur"')

    # Determine length of recording.
    if rec_dur is None:
        rec_dur = max_offset

    # Write speech/nonspeech segmentation.
    def _f2s(x, precision):
        if not precision:
            return x
        x = round(x, precision)
        return f'{x:.{precision}f}'
    def _write_segment(f, onset, offset, label):
        if in_sec:
            onset = _f2s(onset, precision)
            offset = _f2s(offset, precision)
        else:
            onset = int(onset*1e7)
            offset = int(offset*1e7)
        f.write(f'{onset}\t{offset}\t{label}\n')
    if not is_sorted:
        segs = sorted(segs)
    with open(fpath, 'w', encoding='utf-8') as f:
        tmp_segs = [Segment(0, 0)]
        tmp_segs.extend(segs)
        tmp_segs.append(Segment(rec_dur, rec_dur))
        for curr_seg, seg in zip(tmp_segs[:-1], tmp_segs[1:]):
            gap = curr_seg ^ seg
            if curr_seg:
                _write_segment(f, curr_seg.onset, curr_seg.offset, 'speech')
            if gap:
                _write_segment(f, gap.onset, gap.offset, 'non-speech')
