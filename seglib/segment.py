"""Labeled segments."""
from dataclasses import dataclass

from .utils import add_dataclass_slots, clip

__all__ = ['Segment']


# Implementation inspired by pyannote.core.segment.
@add_dataclass_slots
@dataclass(unsafe_hash=True, order=True)
class Segment:
    """Speech segment.

    Parameters
    ----------
    onset : float
        Onset of segment in seconds from beginning of recording.

    offset : float
        Offset of segment in seconds from beginning of recording.
    """
    onset: float
    offset: float

    def gap(self, other):
        """Return gap between segment and another segment.

        If the two segments overlap, the gap will have duration <= 0.

        Parameter
        ---------
        other : Segment
            Other segment.

        Returns
        -------
        Segment
            Gap segment.
        """
        onset = min(self.offset, other.offset)
        offset = max(self.onset, other.onset)
        return Segment(onset, offset)

    def union(self, *other):
        """Return union of segments.

        The union of a set of segments is defined as the minimal segment
        containing each segment in the set.

        Parameter
        ---------
        other : Segment
            Other segment.

        Returns
        -------
        Segment
            Union of the segments.
        """
        segs = [self]
        segs.extend(other)
        onset =	min(s.onset for s in segs)
        offset = max(s.offset for s in segs)
        return Segment(onset, offset)

    def copy(self):
        """Return deep copy of segment."""
        return Segment(onset=self.onset, offset=self.offset)

    def shift(self, delta, in_place=False):
        """Shift segment by ``delta`` seconds."""
        if not in_place:
            self = self.copy()
        self.onset += delta
        self.offset += delta
        return self

    def clip(self, lb, ub, in_place=False):
        """Clip segment so that its onset/offset lay within [``lb``, ``ub``].

        Parameters
        ----------
        lb : float
            Lowerbound of interval.

        ub : float
            Upperbound of interval.

        in_place : bool, optional
            If True, perform operation in place.

        Returns
        -------
        Segment
            Clipped segment.
        """
        if not in_place:
            self = self.copy()
        self.onset = clip(self.onset, lb, ub)
        self.offset = clip(self.offset, lb, ub)
        return self

    def round(self, precision=3, in_place=False):
        """Round onset/offset to `precision` digits."""
        if not in_place:
            self = self.copy()
        self.onset = round(self.onset, precision)
        self.offset = round(self.offset, precision)
        return self

    @property
    def duration(self):
        """Segment duration in seconds."""
        return self.offset - self.onset

    def __iter__(self):
        """Unpack segment for easy interoperability with tuples.

        >>> seg = Segment(0.1, 0.5)
        >>> onset, offset = seg
        """
        yield self.onset
        yield self.offset

    def __bool__(self):
        return self.duration > 0

    def __or__(self, other):
        return self.union(other)

    def __xor__(self, other):
        return self.gap(other)

    def __ne__(self, other):
        return not self.__eq__(other)


def merge_segs(segs, thresh=0.0, is_sorted=False, copy=True):
    """Merge segments.

    Produces a new segmentation from `segs` by:

    - merging overlapping segments
    - merging segments separated by <= `thresh` seconds.

    Parameters
    ----------
    segs : list of Segment
        Segments to be merged.

    thresh : float, optional
        Tolerance for merging. Segments separated by <= `thresh` seconds
        will be merged.
        (Default: 0.0)

    is_sorted : bool, optional
        If True, treat `segs` as already sorted. Otherwise, sort before
        performing mergers.
        (Default: False)

    copy : bool, optional
        If True, create copy of `segs` and perform merger on this copy.
        (Default: True)

    Returns
    -------
    list of Segment
        Merged segments.
    """
    if copy:
        segs = [seg.copy() for seg in segs]
    if not is_sorted:
        segs = sorted(segs)

    # Perform merger.
    merged_segs = []
    curr_seg = segs[0]
    for seg in segs:
        gap = curr_seg ^ seg
        if gap.duration > thresh:
            merged_segs.append(curr_seg)
            curr_seg = seg
        curr_seg = curr_seg | seg
    merged_segs.append(curr_seg)

    return merged_segs
