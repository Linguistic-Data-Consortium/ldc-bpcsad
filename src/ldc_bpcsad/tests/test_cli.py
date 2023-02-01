# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
from pathlib import Path

import pytest
from soundfile import LibsndfileError, SoundFileError

from ldc_bpcsad.cli import (
    load_htk_script_file, load_json_script_file, Channel, ChannelNotFoundError,
    FileEmptyError)


TEST_DIR = Path(__file__).parent
AUDIO_DIR = TEST_DIR / 'audio'
GOOD_FLAC_PATH = AUDIO_DIR / 'good.flac'


class TestValidateChannel:
    def test_good_file(self, caplog):
        channel = Channel('good_c1', GOOD_FLAC_PATH, 1)
        assert channel.validate()
        assert 'Audio file does not exist' not in caplog.text
        assert 'Problem reading audio file' not in caplog.text
        assert 'Invalid channel' not in caplog.text

    def test_bad_audio_path(self):
        # File does not exist.
        channel = Channel('exist', '/does/not/exist.flac', 1)
        with pytest.raises(FileNotFoundError) as excinfo:
            channel.validate()
        assert 'Audio file does not exist' in str(excinfo.value)

    def test_unknown_format(self):
        # Unknown file extension.
        channel = Channel('unk_fmt_c1', AUDIO_DIR / 'unk_fmt.txt', 1)
        with pytest.raises(SoundFileError) as excinfo:
            channel.validate()

        # Known file extension, but cannot read contents. E.g., corrupted or
        # wrong extension.
        channel = Channel('corrupted_c1', AUDIO_DIR / 'corrupted.flac', 1)
        with pytest.raises(LibsndfileError) as excinfo:
            channel.validate()

    def test_empty_file(self):
        channel = Channel('empty', AUDIO_DIR / 'empty.flac', 1)
        with pytest.raises(FileEmptyError) as excinfo:
            channel.validate()
        assert 'File contains no data.' in str(excinfo.value)

    @pytest.mark.parametrize('chan_num', [0, 2])
    def test_bad_channel(self, chan_num):
        # Channel does not exist for file (no logging).
        channel = Channel('good', GOOD_FLAC_PATH, chan_num)
        with pytest.raises(ChannelNotFoundError) as excinfo:
            channel.validate()
        assert 'Invalid channel' not in str(excinfo.value)


class TestLoadHTKScriptFile:
    def test_valid(self, tmpdir):
        # Properly formed script file.
        expected = [Channel('good', GOOD_FLAC_PATH, 1)]
        htk_txt = f'{GOOD_FLAC_PATH}\n'
        scp_path = Path(tmpdir, 'valid.scp')
        scp_path.write_text(htk_txt)
        actual = load_htk_script_file(scp_path, channel=1)
        assert actual == expected


class TestLoadJSONScriptFile:
    def test_valid(self, tmpdir):
        # Properly formed script file.
        expected = [Channel('good_c1', GOOD_FLAC_PATH, 1)]
        json_txt = (f'[{{"channel_id": "good_c1", '
                    f'"audio_path": "{GOOD_FLAC_PATH}", '
                    f'"channel": 1}}]')
        scp_path = Path(tmpdir, 'valid.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected

    def test_missing_channel_id(self, tmpdir, caplog):
        # Missing channel URI.
        expected = []
        json_txt = f'[{{"audio_path": "{GOOD_FLAC_PATH}", "channel": 1}}]'
        scp_path = Path(tmpdir, 'missing_chanid.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected
        assert 'Malformed record' in caplog.text

    def test_missing_audio_path(self, tmpdir, caplog):
        # Missing audio path.
        expected = []
        json_txt = '[{"channel_id": "good_c1", "channel": 1}]'
        scp_path = Path(tmpdir, 'missing_apath.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected
        assert 'Malformed record' in caplog.text

    def test_missing_channel(self, tmpdir, caplog):
        # Missing audio path.
        expected = []
        json_txt = (f'[{{"channel_id": "good_c1", '
                    f'"audio_path": "{GOOD_FLAC_PATH}"}}]')
        scp_path = Path(tmpdir, 'missing_chan.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected
        assert 'Malformed record' in caplog.text
