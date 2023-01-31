# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
"""Common functions for IO."""
import math

__all__ = ['check_segs']


def check_segs(segs, rec_dur=None, abs_tol=1e-6):
    """Input validation on a list of segments.

    By default, checks that:

    - each segment has non-zero duration
    - no onset falls before 0
    - no offset falls after the end of the recording

    Parameters
    ----------
    segs : list of Segment
        Segments to validate.

    rec_dur : float, optional
        Recording duration. If None, set to offset of last segment.
        (Default: None)

    abs_tol : float, optional
        Tolerance for determining equality.
        (Default: 1e-8)

    Returns
    -------
    segs
    rec_dur
    """
    def _is_close(a, b):
        return math.isclose(a, b, abs_tol=abs_tol)

    # Check that one of segs/rec_dur is set.
    if not segs and rec_dur is None:
        raise ValueError('if "segs" is empty, "rec_dur" must be set')

    # Check recording duration is > 0.
    if rec_dur is None:
        rec_dur = max(seg.offset for seg in segs)
    if _is_close(rec_dur, 0) or rec_dur < 0:
        raise ValueError(
            f'Recording duration {rec_dur} seconds is <= 0.')
    for seg in segs:
        # Check non-zero duration.
        if seg.duration < 0 or _is_close(seg.duration, 0):
            raise ValueError(f'Segment {seg} has non-positive duration.')

        # Check on interval [0, rec_dur].
        illegal_onset = seg.onset < 0 and not _is_close(seg.onset, 0)
        illegal_offset = (seg.offset > rec_dur and
                          not _is_close(seg.offset, rec_dur))
        if illegal_onset or illegal_offset:
            raise ValueError(
                f'Segment {seg} is not on interval [0, {rec_dur}].')

    return segs, rec_dur
