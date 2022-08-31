# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for segmenting recordings."""
from pathlib import Path
import shutil
import tempfile

import soundfile as sf

from .htk import hvite, write_hmmdefs, HTKError, HViteConfig
from .io import load_htk_label_file
from .logging import getLogger
from .segment import merge_segs
from .utils import resample

__all__ = ['decode']


logger = getLogger()


THIS_DIR = Path(__file__).parent

# Model directory for pre-trained model.
MODEL_DIR = THIS_DIR / 'model'

# Names of phones corresponding to broad phonetic classes.
SPEECH_PHONES = ['f',  # Fricative.
                 'g',  # Glide/liquid.
                 'n',  # Nasal.
                 's',  # Stop/affricate.
                 'v',  # Vowel.
                ]


class DecodingError(Exception):
    """Error segmenting file."""


def _decode_chunk(x, sr, bi, ei, min_chunk_len, hvite_config):
    """Perform speech activity detection on a single channel of an audio file.

    Decodes the chunk `x[bi:ei)`.

    Parameters
    ----------
    x : TODO
    sr : TODO
    bi : int
        Index of first sample of chunk.

    ei : int
        Index of last sample of chunk.

    min_chunk_len : int
        Minimum size of chunk in samples.

    hvite_config : HViteConfig
        TODO
    """
    # Convert from samples to seconds for more human-readable exceptions and
    # logging.
    rec_len = len(x)
    rec_dur = rec_len / sr
    chunk_len = ei - bi
    chunk_onset = bi / sr
    chunk_offset = ei / sr
    chunk_dur = chunk_len / sr

    # Base case: Chunk length < minimum chunk length. We make an exception
    # for when the chunk is equal to x as we want to guarantee HVite is
    # always called at least once, no matter how short the audio.
    if (chunk_len < rec_len and chunk_len < min_chunk_len):
        min_chunk_dur = min_chunk_len / sr
        raise DecodingError(
            f'Minimum chunk duration reached: {chunk_dur} < {min_chunk_dur}')

    # Actually attempt decoding via HVite.
    # TODO: Move recursion outside of try...except block.
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        # Base case: HVite finishes successfully; return segments.
        logger.debug(
            f'Attempting decoding for chunk: RECORDING_DUR: {rec_dur:.3f}, '
            f'CHUNK_DUR: {chunk_dur:.3f}, CHUNK_ONSET: {chunk_onset:.3f}, '
            f'CHUNK_OFFSET: {chunk_offset:.3f}')
        wav_path = tmp_dir / 'chunk.wav'
        sf.write(wav_path, x[bi:ei+1], sr, 'PCM_16')
        lab_path = hvite(
            wav_path, hvite_config, tmp_dir)
        segs = load_htk_label_file(
            lab_path, target_labels=['speech'], in_sec=False)
        segs = [seg.shift(chunk_onset) for seg in segs]
        logger.debug(
            f'Successfully decoded chunk:    RECORDING_DUR: {rec_dur:.3f}, '
            f'CHUNK_DUR: {chunk_dur:.3f}, CHUNK_ONSET: {chunk_onset:.3f}, '
            f'CHUNK_OFFSET: {chunk_offset:.3f}')
    except HTKError:
        # Recursive case: Retry HVite on two shorter chunks.
        mid = (bi + ei) // 2
        segs = _decode_chunk(x, sr, bi, mid, min_chunk_len, hvite_config)
        segs.extend(
            _decode_chunk(x, sr, mid, ei, min_chunk_len, hvite_config))
    finally:
        shutil.rmtree(tmp_dir)

    return segs


def decode(x, sr, min_speech_dur=0.500, min_nonspeech_dur=0.300,
            min_chunk_dur=10, max_chunk_dur=3600, speech_scale_factor=1):
    """Perform speech activity detection on a single channel of an audio file.

    The resulting segmentation will be saved in an HTK label file in
    ``lab_dir`` with the same name as ``audio_path`` but file extension ``ext``.

    Because HTK's `HVite` command sometimes fails for longer recordings, we
    first split `x` into chunks of at most `max_chunk_dur` seconds, segment
    each chunk separately, then merge the results. The individual chunks are
    segmented using a recursive approach that calls `HVite` with progressively
    smaller chunks until a minimum chunk duration (`min_chunk_dur`) is reached.

    Parameters
    ----------
    x : ndarray (n_samples)
        Audio samples.

    sr : int
        Sample rate (Hz).

    min_speech_dur : float, optional
        Minimum duration of speech segments in seconds.
        (Default: 0.500)

    min_nonspeech_dur : float, optional
        Minimum duration of nonspeech segments in seconds.
        (Default: 0.300)

    min_chunk_dur : float, optional
        Minimum duration in seconds of chunk SAD may be performed on when
        splitting long recordings.
        (Default: 10.0)

    max_chunk_dur : float, optional
        Maximum duration in seconds of chunk SAD may be performed on when
        splitting long recordings.
        (Default: 3600.0)

    speech_scale_factor : float, optional
        Factor by which speech model acoustic likelihoods are scaled prior to
        beam search. Larger values will bias the SAD engine in favour of more
        speech segments.
        (Default: 1)

    Returns
    -------
    segs : TODO

    Raises
    ------
    DecodingError
    """
    try:
        # Load model.
        hvite_config = HViteConfig.from_model_dir(MODEL_DIR)
        new_hmmdefs_path = Path(tempfile.mktemp())
        write_hmmdefs(
            hvite_config.hmmdefs_path, new_hmmdefs_path, speech_scale_factor,
            SPEECH_PHONES)
        hvite_config.hmmdefs_path = new_hmmdefs_path

        # Resample x to 16 kHz for feature extraction.
        if sr != 16000:
            x = resample(x, sr, 16000)
            sr = 16000

        # Determine boundaries of the chunks for segmentation.
        n_samples = len(x)
        min_chunk_len = min(int(min_chunk_dur * sr), n_samples)
        max_chunk_len = min(int(max_chunk_dur * sr), n_samples)
        if n_samples <= max_chunk_len:
            bounds = [0, n_samples]
        else:
            bounds = list(range(0, n_samples, max_chunk_len))
            final_chunk_len = n_samples - bounds[-1]
            if final_chunk_len < min_chunk_len:
                # Absorb remainder of x into final chunk.
                bounds[-1] = n_samples
            else:
                # Assign remainder of x to its own chunk.
                bounds.append(n_samples)
        chunks = list(zip(bounds[:-1], bounds[1:]))

        # Segment.
        segs = []
        for bi, ei in chunks:
            segs_ = _decode_chunk(x, sr, bi, ei, min_chunk_len, hvite_config)
            segs.extend(segs_)

        # Smoothe segmentation by:
        #   - merging speech segments separated by < min_nonspeech_dur seconds
        #   - filtering speech segments < min_speech_dur seconds
        min_nonspeech_dur = max(min_nonspeech_dur, 0.010)  # Gaps < 10 ms are artifacts.
        segs = merge_segs(segs, thresh=min_nonspeech_dur, copy=False)
        if segs:
            # Extend speech segments at beginning/end of recording if the
            # adjacent gaps are <= min_speech_dur seconds.
            if segs[0].onset <= min_nonspeech_dur:
                segs[0].onset = 0
            rec_dur = len(x) / sr
            if (rec_dur - segs[-1].offset) <= min_nonspeech_dur:
                segs[-1].offset = rec_dur
        segs = [seg for seg in segs if seg.duration >= min_speech_dur]
    except DecodingError as e:
        raise e
    finally:
        new_hmmdefs_path.unlink()


    return segs
