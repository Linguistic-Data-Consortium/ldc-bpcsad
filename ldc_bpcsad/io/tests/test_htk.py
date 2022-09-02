from pathlib import Path
import pytest

from ldc_bpcsad.io.htk import load_htk_label_file, write_htk_label_file
from ldc_bpcsad.segment import Segment


@pytest.fixture
def data_sec():
    data = ('0.0 2.0 sil\n'
            '2.0 2.5 word1\n'
            '2.5 3.0 sil\n'
            '3.0 3.5 word2\n'
            '3.5 5.0 sil\n')
    return data.replace(' ', '\t')


@pytest.fixture
def path_sec(data_sec, tmpdir):
    path = Path(tmpdir, 'data_sec.lab')
    path.write_text(data_sec)
    return path


@pytest.fixture
def data_htk():
    data = ('0 20000000 sil\n'
            '20000000 25000000 word1\n'
            '25000000 30000000 sil\n'
            '30000000 35000000 word2\n'
            '35000000 50000000 sil\n')
    return data.replace(' ', '\t')


@pytest.fixture
def path_htk(data_htk, tmpdir):
    path = Path(tmpdir, 'data_htk.lab')
    path.write_text(data_htk)
    return path


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


def test_load_htk_label_file(path_sec, path_htk, all_segs, speech_segs):
    # No filtering.
    expected = all_segs
    actual = load_htk_label_file(path_sec)
    assert actual == expected

    # Filter non-speech using target_labels.
    expected = speech_segs
    actual = load_htk_label_file(
        path_sec, target_labels={'word1', 'word2', 'word3'})
    assert actual == expected

    # Filter non-speech using ignored_labels.
    expected = speech_segs
    actual = load_htk_label_file(
        path_sec, ignored_labels={'sil'})
    assert actual == expected

    # Test import from file using HTK units instead of seconds.
    expected = all_segs
    actual = load_htk_label_file(path_htk, in_sec=False)
    assert actual == expected

    # Check args validation.
    with pytest.raises(ValueError):
        load_htk_label_file(
            path_sec, target_labels={'word1', 'word2', 'word3'},
            ignored_labels={'sil'})


def test_write_htk_label_file(speech_segs, tmpdir):
    # Write in seconds.
    expected = ('0.0 2.0 non-speech\n'
                '2.0 2.5 speech\n'
                '2.5 3.0 non-speech\n'
                '3.0 3.5 speech\n'
                '3.5 5.0 non-speech\n')
    expected = expected.replace(' ', '\t')
    actual_path_sec = Path(tmpdir, 'actual_data_sec.lab')
    write_htk_label_file(
        actual_path_sec, speech_segs, rec_dur=5.0, precision=1)
    actual = actual_path_sec.read_text()
    assert actual == expected

    # Write in HTK units.
    expected = ('0 20000000 non-speech\n'
                '20000000 25000000 speech\n'
                '25000000 30000000 non-speech\n'
                '30000000 35000000 speech\n'
                '35000000 50000000 non-speech\n')
    expected = expected.replace(' ',  '\t')
    actual_path_htk = Path(tmpdir, 'actual_data_htk.lab')
    write_htk_label_file(actual_path_htk, speech_segs, rec_dur=5.0, in_sec=False)
    actual = actual_path_htk.read_text()
    assert actual == expected

    # Recording duration not specified.
    expected = ('0.0 2.0 non-speech\n'
                '2.0 2.5 speech\n'
                '2.5 3.0 non-speech\n'
		'3.0 3.5 speech\n')
    expected = expected.replace(' ',  '\t')
    actual_path = Path(tmpdir, 'no_recdur_sec.lab')
    write_htk_label_file(actual_path, speech_segs, precision=1)
    actual = actual_path.read_text()
    assert actual == expected

    # Empty segmentation.
    expected = '0.0 5.0 non-speech\n'.replace(' ', '\t')
    actual_path = Path(tmpdir, 'no_segs_sec.lab')
    write_htk_label_file(actual_path, [], rec_dur=5.0, precision=1)
    actual = actual_path.read_text()
    assert actual == expected
