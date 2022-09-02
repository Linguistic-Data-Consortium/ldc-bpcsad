import numpy as np
import pytest
import soundfile as sf

import ldc_bpcsad.decode
import ldc_bpcsad.htk


orig_hvite = ldc_bpcsad.htk.hvite


# Config for hvite.

@pytest.fixture
def hvite_config():
    return ldc_bpcsad.htk.HViteConfig.from_model_dir(
        ldc_bpcsad.decode.MODEL_DIR)


# Seed for NumPy RNG.
SEED = 123015602

# No speech recording duration (seconds).
NOSPEECH_DUR = 100

# Sample rate (Hz) of audio.
SR = 16000

@pytest.fixture
def x_nospeech(scale=0.01):
    """Sample `dur` second long signal containing **NO SPEECH**.."""
    np.random.seed(SEED)
    n_samples = int(NOSPEECH_DUR*SR)
    x = 2*scale*np.random.rand(n_samples) - scale
    x = np.clip(x, -1, 1)
    return x


def hvite_fail_gt40(wav_path, config, working_dir):
    """Version of `hvite` that fails on recordings > 40 seconds duration.

    Used for testing how `ldc_bpcsad.decode._decode_chunk` handles errors.
    """
    rec_dur = sf.info(wav_path).duration
    if rec_dur > 40:
        raise ldc_bpcsad.htk.HTKError
    return ldc_bpcsad.htk.hvite(wav_path, config, working_dir)


class TestDecodeChunk():
    def test_no_hvite_failures(self, x_nospeech, hvite_config, mocker):
        # Dcode succeeds for entire 100 chunk recording of silence with NO
        # HVite failures.
        # recording of silence.
        spy = mocker.spy(ldc_bpcsad.decode, 'hvite')
        min_chunk_dur = 10
        min_chunk_len = int(min_chunk_dur*SR)
        segs = ldc_bpcsad.decode._decode_chunk(
            x_nospeech, SR, 0, x_nospeech.size, min_chunk_len, hvite_config)

        # Check that no recursion occurred.
        assert spy.call_count == 1

        # And that no speech was detected.
        assert segs == []

    def test_hvite_failures(self, x_nospeech, hvite_config, monkeypatch,
                            mocker):
        # Simulate HVite failure on chunks > 40 seconds using a 100 second
        # recording of silence.
        monkeypatch.setattr(ldc_bpcsad.decode, 'hvite', hvite_fail_gt40)
        spy = mocker.spy(ldc_bpcsad.decode, 'hvite')
        min_chunk_dur = 10
        min_chunk_len = int(min_chunk_dur*SR)
        segs = ldc_bpcsad.decode._decode_chunk(
            x_nospeech, SR, 0, x_nospeech.size, min_chunk_len, hvite_config)

        # Check that recursion actually occurred.
        assert spy.call_count == 7

        # And that no speech was detected.
        assert segs == []


class TestDecode:
    def test_no_chunking(self, x_nospeech, mocker):
        spy = mocker.spy(ldc_bpcsad.decode, '_decode_chunk')
        segs = ldc_bpcsad.decode.decode(
            x_nospeech, SR, min_chunk_dur=10, max_chunk_dur=1000)
        assert len(segs) == 0
        assert spy.call_count == 1


    def test_chunking(self, x_nospeech, mocker):
        spy = mocker.spy(ldc_bpcsad.decode, '_decode_chunk')
        segs = ldc_bpcsad.decode.decode(
            x_nospeech, SR, min_chunk_dur=10, max_chunk_dur=40)
        assert len(segs) == 0
        assert spy.call_count == 3
