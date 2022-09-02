"""Tests for utility functions."""
import pytest

from ldc_bpcsad.utils import clip


def test_clip():
    x = 10
    assert clip(x, 12, 20) == 12
    assert clip(x, 1, 8) == 8
    with pytest.raises(ValueError) as e:
        clip(1, 2, 0)
