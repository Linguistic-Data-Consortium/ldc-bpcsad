from pathlib import Path

import pytest

from ldc_bpcsad.cli import (load_htk_script_file, load_json_script_file,
                            Channel)


TEST_DIR = Path(__file__).parent
REC1_PATH = TEST_DIR /  'rec01.flac'


class TestValidateChannel:
    def test_good_file(self, caplog):
        channel = Channel('rec01_c1', REC1_PATH, 1)
        assert channel.validate(log=True)
        assert 'Audio file does not exist' not in caplog.text
        assert 'Problem reading audio file' not in caplog.text
        assert 'Invalid channel' not in caplog.text

    def test_bad_audio_path(self, caplog):
        # File does not exist (no logging).
        channel = Channel('exist', '/does/not/exist.flac', 1)
        assert not channel.validate(log=False)
        assert 'Audio file does not exist' not in caplog.text

        # File does not exist (logging).
        channel = Channel('exist', '/does/not/exist.flac', 1)
        assert not channel.validate(log=True)
        assert 'Audio file does not exist' in caplog.text

    @pytest.mark.parametrize('chan_num', [0, 2])
    def test_bad_channel(self, chan_num, caplog):
        # Channel does not exist for file (no logging).
        channel = Channel('rec01', REC1_PATH, chan_num)
        assert not channel.validate(log=False)
        assert 'Invalid channel' not in caplog.text

        # Channel does not exist for file (logging).
        channel = Channel('rec01', REC1_PATH, chan_num)
        assert not channel.validate(log=True)
        assert 'Invalid channel' in caplog.text


class TestLoadHTKScriptFile:
    def test_valid(self, tmpdir):
        # Properly formed script file.
        expected = [Channel('rec01', REC1_PATH, 1)]
        htk_txt = f'{REC1_PATH}\n'
        scp_path = Path(tmpdir, 'valid.scp')
        scp_path.write_text(htk_txt)
        actual = load_htk_script_file(scp_path, channel=1)
        assert actual == expected


class TestLoadJSONScriptFile:
    def test_valid(self, tmpdir):
        # Properly formed script file.
        expected = [Channel('rec01_c1', REC1_PATH, 1)]
        json_txt = (f'[{{"uri": "rec01_c1", "audio_path": "{REC1_PATH}", '
                    f'"channel": 1}}]')
        scp_path = Path(tmpdir, 'valid.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected

    def test_missing_uri(self, tmpdir, caplog):
        # Missing channel URI.
        expected = []
        json_txt = f'[{{"audio_path": "{REC1_PATH}", "channel": 1}}]'
        scp_path = Path(tmpdir, 'missing_uri.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected
        assert 'Malformed record' in caplog.text

    def test_missing_audio_path(self, tmpdir, caplog):
        # Missing audio path.
        expected = []
        json_txt = '[{"uri": "rec01_c1", "channel": 1}]'
        scp_path = Path(tmpdir, 'missing_apath.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected
        assert 'Malformed record' in caplog.text

    def test_missing_channel(self, tmpdir, caplog):
        # Missing audio path.
        expected = []
        json_txt = f'[{{"uri": "rec01_c1", "audio_path": "{REC1_PATH}"}}]'
        scp_path = Path(tmpdir, 'missing_chan.scp')
        scp_path.write_text(json_txt)
        actual = load_json_script_file(scp_path)
        assert actual == expected
        assert 'Malformed record' in caplog.text
