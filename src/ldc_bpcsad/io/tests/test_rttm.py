# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: GNU General Public License v3.0
from pathlib import Path

import pytest

from ldc_bpcsad.io.rttm import (load_rttm_file, write_rttm_file)
from ldc_bpcsad.segment import Segment


allclose = Segment.allclose

@pytest.fixture
def rttm_path(tmpdir):
    data = ('SPEAKER rec1.flac 1 1.05 2.45 <NA> <NA> speaker <NA> <NA>\n'
            'SPEAKER rec1.flac 1 4.00 3.31 <NA> <NA> speaker <NA> <NA>\n'
            'SPEAKER rec1.flac 1 10.11 4.15 <NA> <NA> speaker <NA> <NA>\n')
    rttm_path = Path(tmpdir, 'rec1.rttm')
    rttm_path.write_text(data)
    return rttm_path


@pytest.fixture
def speech_segs():
    return [Segment(1.05, 3.5),
            Segment(4.0, 7.31),
            Segment(10.11, 14.26)]


def test_load_rttm_file(rttm_path, speech_segs):
    expected = list(speech_segs)
    actual = load_rttm_file(rttm_path)
    assert allclose(actual, expected)


def test_write_rttm_file(rttm_path, speech_segs, tmpdir):
    # Write in seconds.
    expected = rttm_path.read_text()
    actual_path = Path(tmpdir, 'actual_data.rttm')
    write_rttm_file(
        actual_path, speech_segs, file_id='rec1.flac', channel=1, precision=2)
    actual = actual_path.read_text()
    assert actual == expected
