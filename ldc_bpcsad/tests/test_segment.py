# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Tests for `Segment`."""
import pytest

from ldc_bpcsad.segment import merge_segs, Segment


def assert_turn_equal(t1, t2, excluded_fields=None):
    if excluded_fields is None:
        excluded_fields = set()
    try:
        assert type(t1) is type(t2)
        for field in t1.__dataclass_fields__:
            if field in excluded_fields:
                continue
            assert getattr(t1, field) == getattr(t2, field)
    except AssertionError:
        raise AssertionError


class TestSegment:
    def test_creation(self):
        s = Segment(0, 1)
        assert s.onset == 0
        assert s.offset == 1

    def test_gap(self):
        # No overlap.
        seg1 = Segment(1, 1.5)
        seg2 = Segment(2, 2.5)
        assert seg1.gap(seg2) == Segment(1.5, 2)

    def test_union(self):
        # Two segments.
        s1 = Segment(0, 1)
        s2 = Segment(2, 3)
        assert s1.union(s2) == Segment(0, 3)

        # Three segments.
        s3 = Segment(4, 5)
        assert s1.union(s2, s3) == Segment(0, 5)

        # Called as a function.
        assert Segment.union(s1, s2, s3) == Segment(0, 5)

    def test_shift(self):
        s =	Segment(0, 1)
        s_shifted = Segment(5, 6)

        s1 = s.copy()
        s2 = s1.shift(5)
        assert s2 == s_shifted
        assert s1 == s

        # In place.
        s1 = s.copy()
        s1.shift(5, in_place=True)
        assert s1 == s_shifted

    def test_clip(self):
        s = Segment(0, 1)
        s_clipped = Segment(0.6, 0.8)

        s1 = s.copy()
        s2 = s1.clip(0.6, 0.8)
        assert s2 == s_clipped
        assert s1 == s

        # In place.
        s1 = s.copy()
        s1.clip(0.6, 0.8, in_place=True)
        assert s1 == s_clipped

    def test_round(self):
        s = Segment(0.1231, 4.1235)
        s_rounded = Segment(0.123, 4.123)

        s1 = s.copy()
        s2 = s1.round(3)
        assert s2 == s_rounded
        assert s1 == s

        # In place.
        s1 = s.copy()
        s1.round(3, in_place=True)
        assert s1 == s_rounded

    def test_duration(self):
        s = Segment(0, 1)
        assert s.duration == 1

    def test_bool(self):
        assert Segment(0, 1)
        assert not Segment(0, 0)
        assert not Segment(0, -1)

    def test_or(self):
        seg1 = Segment(1, 1.5)
        seg2 = Segment(2, 2.5)
        assert seg1.union(seg2) == seg1 | seg2
        assert seg1.union(seg2) == seg2 | seg1

    def test_xor(self):
        seg1 = Segment(1, 1.5)
        seg2 = Segment(2, 2.5)
        assert seg1.gap(seg2) == seg1 ^ seg2
        assert seg1.gap(seg2) == seg2 ^ seg1


@pytest.fixture
def segs():
    return [
        Segment(7.20, 8.00),
        Segment(8.25, 9.00),
        Segment(0.10, 1.45),
        Segment(4.10, 6.20),
        Segment(6.20, 7.00),
        Segment(9.251, 10.00),
        Segment(0.45, 1.00)]


def test_merge_segs(segs):
    # Test adjacent segments.
    expected_segs = [Segment(1, 5)]
    premerge_segs = [
        Segment(1, 3),
        Segment(3, 5)]
    assert expected_segs == merge_segs(premerge_segs)

    # Test segments separated by <= collar seconds that are NOT adjacent
    expected_segs = [Segment(1, 5)]
    premerge_segs = [
	Segment(1, 3),
        Segment(3.20, 5)]
    assert expected_segs == merge_segs(premerge_segs, thresh=0.250)

    # Test segments separated by EXACTLY collar seconds.
    expected_segs = [Segment(1, 5)]
    premerge_segs = [
	Segment(1, 3),
        Segment(3.25, 5)]
    assert expected_segs == merge_segs(premerge_segs, thresh=0.250)

    # Test segments separated by more than collar seconds.
    expected_segs = [Segment(1, 3), Segment(3.251, 5)]
    premerge_segs = [
	Segment(1, 3),
        Segment(3.251, 5)]
    assert expected_segs == merge_segs(premerge_segs, thresh=0.250)

    # Full test.
    expected_segs = [
        Segment(0.10, 1.45),
        Segment(4.10, 9.0),
        Segment(9.251, 10.00)]
    assert expected_segs == merge_segs(segs, thresh=0.250)
    assert expected_segs == merge_segs(sorted(segs), thresh=0.250, is_sorted=True)
