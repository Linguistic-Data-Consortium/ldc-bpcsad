# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
from pathlib import Path

import pytest

from ldc_bpcsad.io.textgrid import write_textgrid_file
from ldc_bpcsad.segment import Segment


@pytest.fixture
def tg_path(tmpdir):
    data = ('File type = "ooTextFile"\n'
            'Object class = "TextGrid"\n'
            '\n'
            'xmin = 0\n'
            'xmax = 5.0\n'
            'tiers? <exists>\n'
            'size = 1\n'
            'item []:\n'
            '    item [1]:\n'
            '        class = "IntervalTier"\n'
            '        name = "sad"\n'
            '        xmin = 0\n'
            '        xmax = 5.0\n'
            '        intervals: size = 5\n'
            '        intervals [1]:\n'
            '            xmin = 0\n'
            '            xmax = 2.0\n'
            '            text = "non-speech"\n'
            '        intervals [2]:\n'
            '            xmin = 2.0\n'
            '            xmax = 2.5\n'
            '            text = "speech"\n'
            '        intervals [3]:\n'
            '            xmin = 2.5\n'
            '            xmax = 3.0\n'
            '            text = "non-speech"\n'
            '        intervals [4]:\n'
            '            xmin = 3.0\n'
            '            xmax = 3.5\n'
            '            text = "speech"\n'
            '        intervals [5]:\n'
            '            xmin = 3.5\n'
            '            xmax = 5.0\n'
            '            text = "non-speech"\n')
    tg_path = Path(tmpdir, 'rec1.TextGrid')
    tg_path.write_text(data)
    return tg_path


@pytest.fixture
def speech_segs():
    return [Segment(2.0, 2.5),
            Segment(3.0, 3.5)]


def test_write_textgrid_file(tg_path, speech_segs, tmpdir):
    # Write in seconds.
    expected = tg_path.read_text()
    actual_path = Path(tmpdir, 'actual_data.tg')
    write_textgrid_file(
        actual_path, speech_segs, tier='sad', rec_dur=5.0, is_sorted=True,
        precision=1)
    actual = actual_path.read_text()
    print(expected)
    print(actual)
    assert actual == expected
