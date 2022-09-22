# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
from pathlib import Path
import pytest

from ldc_bpcsad.io.audacity import (load_audacity_label_file,
                                    write_audacity_label_file)
from ldc_bpcsad.segment import Segment


@pytest.fixture
def lab_path(tmpdir):
    data = ('0.0 2.0 sil\n'
            '2.0 2.5 word1\n'
            '2.5 3.0 sil\n'
            '3.0 3.5 word2\n'
            '3.5 5.0 sil\n')
    data = data.replace(' ', '\t')
    lab_path = Path(tmpdir, 'data_sec.lab')
    lab_path.write_text(data)
    return lab_path


@pytest.fixture
def all_segs():
    return [Segment(0.0, 2.0),
            Segment(2.0, 2.5),
            Segment(2.5, 3.0),
            Segment(3.0, 3.5),
            Segment(3.5, 5.0)]


@pytest.fixture
def speech_segs():
    return [Segment(2.0, 2.5),
            Segment(3.0, 3.5)]


def test_load_htk_label_file(lab_path, all_segs, speech_segs):
    # No filtering.
    expected = all_segs
    actual = load_audacity_label_file(lab_path)
    assert actual == expected

    # Filter non-speech using target_labels.
    expected = speech_segs
    actual = load_audacity_label_file(
        lab_path, target_labels={'word1', 'word2', 'word3'})
    assert actual == expected

    # Filter non-speech using ignored_labels.
    expected = speech_segs
    actual = load_audacity_label_file(
        lab_path, ignored_labels={'sil'})
    assert actual == expected

    # Check args validation.
    with pytest.raises(ValueError):
        load_audacity_label_file(
            lab_path, target_labels={'word1', 'word2', 'word3'},
            ignored_labels={'sil'})


def test_write_audacity_label_file(speech_segs, tmpdir):
    # Write in seconds.
    expected = ('0.0 2.0 non-speech\n'
                '2.0 2.5 speech\n'
                '2.5 3.0 non-speech\n'
                '3.0 3.5 speech\n'
                '3.5 5.0 non-speech\n')
    expected = expected.replace(' ', '\t')
    actual_path = Path(tmpdir, 'actual_data_sec.lab')
    write_audacity_label_file(
        actual_path, speech_segs, rec_dur=5.0, precision=1)
    actual = actual_path.read_text()
    assert actual == expected

    # Recording duration not specified.
    expected = ('0.0 2.0 non-speech\n'
                '2.0 2.5 speech\n'
                '2.5 3.0 non-speech\n'
		'3.0 3.5 speech\n')
    expected = expected.replace(' ',  '\t')
    actual_path = Path(tmpdir, 'no_recdur_sec.lab')
    write_audacity_label_file(actual_path, speech_segs, precision=1)
    actual = actual_path.read_text()
    assert actual == expected

    # Empty segmentation.
    expected = '0.0 5.0 non-speech\n'.replace(' ', '\t')
    actual_path = Path(tmpdir, 'no_segs_sec.lab')
    write_audacity_label_file(actual_path, [], rec_dur=5.0, precision=1)
    actual = actual_path.read_text()
    assert actual == expected
