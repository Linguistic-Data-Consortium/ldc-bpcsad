# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for segmenting recordings."""
from dataclasses import dataclass
from math import log
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import soundfile as sf

from .io import read_label_file
from .utils import (arange, concat_segs, elim_short_segs, merge_segs,
                    resample)

__all__ = ['HTKConfig', 'segment_file']


THIS_DIR = Path(__file__).parent
MODEL_DIR = THIS_DIR / 'model'  # Directory containing HTK files.


@dataclass
class HTKConfig:
    """TODO"""
    phone_net_path: Path
    macros_path: Path
    hmmdefs_path: Path
    config_path: Path
    dict_path: Path
    monophones_path: Path


class SegmentationError(BaseException): pass


# TODO:
# - resample audio to 16 kHz
# - divide into chunks
# - write chunks to disk as WAV for HTK
# - time doing things this way vs using SoX
def _segment_chunk(x, sr, onset, offset, htk_config):
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

    # Shell out to HTK to segment.
    cmd = ['HVite',
           '-T', '0',
           '-w', str(htk_config.phone_net_path),
           '-l', str(tmp_dir),
           '-H', str(htk_config.macros_path),
           '-H', str(htk_config.hmmdefs_path),
           '-C', str(htk_config.config_path),
           '-p', '-0.3',
           '-s', '5.0',
           '-y', 'lab',
           str(htk_config.dict_path),
           str(htk_config.monophones_path),
           wav_path,
          ]
    with open(os.devnull, 'wb') as f:
        subprocess.call(cmd, stdout=f, stderr=f)
    try:
        lab_path = Path(tmp_dir, 'chunk.lab')
        segs = read_label_file(lab_path, in_sec=False)
    except:
        raise SegmentationError
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
    # Modify GMM weights to account for speech scale factor.
    old_hmmdefs_path = MODEL_DIR / 'hmmdefs'
    new_hmmdefs_path = Path(tempfile.mktemp())
    write_hmmdefs(old_hmmdefs_path, new_hmmdefs_path, speech_scale_factor)
    htk_config = HTKConfig(MODEL_DIR / 'phone_net',
                           MODEL_DIR / 'macros',
                           new_hmmdefs_path,
                           MODEL_DIR  / 'config',
                           MODEL_DIR / 'dict',
                           MODEL_DIR / 'monophones')

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
                bounds = arange(0, rec_dur, max_chunk_dur)
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
                segs = _segment_chunk(x, sr, onset, offset, htk_config)
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
        except SegmentationError:
            max_chunk_dur /= 2.
    if not success:
        raise SegmentationError

    # Remove temporary hmmdefs file.
    new_hmmdefs_path.unlink()

    return segs


def write_hmmdefs(old_hmmdefs_path, new_hmmdefs_path, speech_scale_factor=1):
    """Modify an HTK hmmdefs file in which speech model acoustic likelihoods
    are scaled by ``speech_scale_factor``.

    Parameters
    ----------
    old_hmmdefs_path : Path
        Path to original HTK hmmdefs file.

    new_hmmsdefs_path : str
        Path for modified HTK hmmdefs file. If file already exists, it
        will be overwritten.

    speech_scale_factor : float, optional
        Factor by which speech model acoustic likelihoods are scaled prior to
        beam search. Larger values will bias the SAD engine in favour of more
        speech segments.
        (Default: 1)
    """
    old_hmmdefs_path = Path(old_hmmdefs_path)
    new_hmmdefs_path = Path(new_hmmdefs_path)

    with open(old_hmmdefs_path, 'r', encoding='utf-8') as f:
        with open(new_hmmdefs_path, 'w', encoding='utf-8') as g:
            # Header.
            for _ in range(3):
                g.write(f.readline())

            # Model definitions.
            curr_phone = None
            for line in f:
                if line.startswith('~h'):
                    curr_phone = line[3:].strip('\"\n')
                if line.startswith('<GCONST>') and curr_phone != 'nonspeech':
                    # Modify GCONST only for mixtures of speech models.
                    gconst = float(line[9:-1])
                    gconst += log(speech_scale_factor)
                    line = f'<GCONST> {gconst:.6e}\n'
                g.write(line)
