# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for segmenting recordings."""
from pathlib import Path
import shutil
import tempfile

import numpy as np
import soundfile as sf

from .htk import hvite, write_hmmdefs, HTKError, HViteConfig
from .io import read_label_file
from .utils import (concat_segs, elim_short_segs, merge_segs,
                    resample)

__all__ = ['segment_file']


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


class SegmentationError(BaseException):
    """Error segmenting file."""


def _segment_chunk(x, sr, onset, offset, hvite_config):
    """Segment chunk of channel from audio file."""
    # Temp directory to hold chunk WAV/label file.
    tmp_dir = Path(tempfile.mkdtemp())

    # Save chunk as 16 bit, 16 kHz WAV.
    bi = int(sr*onset)
    ei = int(sr*offset)
    x = x[bi:ei]
    if sr != 16000:
        # Resample to 16 kHz.
        x = resample(x, sr, 16000)
        sr = 16000
    wav_path = Path(tmp_dir, 'chunk.wav')
    sf.write(wav_path, x, sr, 'PCM_16')

    # Decode using HTK and load segments from resulting label file.
    try:
        lab_path = hvite(
            wav_path, hvite_config, tmp_dir)
        segs = read_label_file(lab_path, in_sec=False)
    finally:
        shutil.rmtree(tmp_dir)

    return segs


def segment_file(x, sr, min_speech_dur=0.500, min_nonspeech_dur=0.300,
                 min_chunk_dur=10, max_chunk_dur=3600, speech_scale_factor=1):
    """Perform speech activity detection on a single channel of an audio file.

    The resulting segmentation will be saved in an HTK label file in
    ``lab_dir`` with the same name as ``audio_path`` but file extension ``ext``.

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
    """
    # Load model.
    hvite_config = HViteConfig.from_model_dir(MODEL_DIR)
    new_hmmdefs_path = Path(tempfile.mktemp())
    write_hmmdefs(
        hvite_config.hmmdefs_path, new_hmmdefs_path, speech_scale_factor,
        SPEECH_PHONES)
    hvite_config.hmmdefs_path = new_hmmdefs_path

    # HVite sometimes (and unpredictably) fails on longer recordings, so try to segment
    # using progressively smaller chunks until all succeed, then merge.
    rec_dur = len(x) / sr  # Duration of recording.
    max_chunk_dur = min(max_chunk_dur, rec_dur)
    min_chunk_dur = min(min_chunk_dur, rec_dur)
    while max_chunk_dur >= min_chunk_dur:
        # TODO: Elim max chunk dur.
        # TODO: More straightforward recursion.
        success = False
        try:
            # Split recording into chunks of at most 3000 seconds.
            if rec_dur > max_chunk_dur:
                bounds = np.arange(0, rec_dur, max_chunk_dur)
                suffix_dur = rec_dur - bounds[-1]
                if suffix_dur < min_chunk_dur:
                    # Absorb remainder of recording into final chunk.
                    bounds[-1] = rec_dur
                else:
                    # Add in one final chunk to cover the remainder. Duration is
                    # smaller than the other chunks, but still > our minimum
                    # duration for segmentation.
                    bounds.append(rec_dur)
            else:
                bounds = [0.0, rec_dur]
            chunks = list(zip(bounds[:-1], bounds[1:]))

            # Segment chunks.
            seg_seqs = []
            for onset, offset in chunks:
                segs = _segment_chunk(x, sr, onset, offset, hvite_config)
                dur = offset - onset
                if segs:
                    segs[-1][1] = dur
                seg_seqs.append(segs)
            segs = concat_segs(seg_seqs, rec_dur)

            # Postprocess segmentation:
            # - merge adjacent segments with same level
            # - eliminate short nonspeech segments
            # - eliminate short speech segments
            segs = merge_segs(segs)
            segs = elim_short_segs(
                segs, target_lab='nonspeech', replace_lab='speech',
                min_dur=min_nonspeech_dur)
            segs = merge_segs(segs)
            segs = elim_short_segs(
                segs, target_lab='speech', replace_lab='nonspeech',
                min_dur=min_speech_dur)
            segs = merge_segs(segs)
            success = True
            break
        except HTKError:
            max_chunk_dur /= 2.

    # Remove temporary hmmdefs file.
    new_hmmdefs_path.unlink()

    # Very rarely, the recursive process above will fail to terminate in a
    # valid segmentation. If this happens, give up and raise an exception.
    if not success:
        raise SegmentationError

    return segs
