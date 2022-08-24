#!/usr/bin/env python
# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Perform speech activity detection (SAD) using a GMM-HMM broad phonetic
class recognizer.

To perform SAD for a set of WAV files and store the segmentations in the
directory ``label_dir``:

    python perform_sad.py -L label_dir rec1.wav rec2.wav rec3.wav ...

For each of the WAV files ``rec1.wav``, ``rec2.wav``, ``rec3.wav``, ... a
corresponding label file (``rec1.lab``, ``rec2.lab``, etc) will be created in
``label_dir``. Label files list the detected speech and non-speech segments
with one segment per line, each line having the format:

    ONSET OFFSET LAB

where ``ONSET`` and ``OFFSET`` are the onset and offset of the segment in
seconds and ``LAB`` is one of {speech, nonspeech}. By default these files
will be output with the extension ``.lab``, though this may be changed via the
``-X`` flag.

Alternately, we could have specified the WAV files via a script file of paths
(one per line) using the ``-S`` flag. For instance, assuming ``wav.scp``
contains lines:

    rec1.wav
    rec2.wav
    rec3.wav
    .
    .
    .

then the output of the following will be identical to the original command:

    python perform_sad.py -S wav.scp -L label_dir

**NOTE** that while the preceding examples illustrated SAD using audio in WAV
format, other formats are supported:

    python perform_sad.py -L label_dir rec1.flac rec2.wav rec3.sph ...

Indeed, any audio file format handled by SoX will work, though the exact
composition of this set will depend on your system's installation of SoX.
For a full listing of supported  formats on your system, run ``sox`` from the
command line without any arguments and check the ``AUDIO FILE FORMATS``
section at the bottom.

By default the segmenter post-processes the output to eliminate speech segments
less than 500 ms in duration and nonspeech segments less than 300 ms in
duration. While these defaults are suitable for SAD that is being done as a
precursor to transcription by human annotators, they may be restrictive for
other uses. If necessary, the minimum speech and nonspeech segment durations
may be changed via the ``--speech`` and ``--nonspeech`` flags respectively.
For instance, to instead use minimum durations of 250 ms for speech and 100 ms
for nonspeech:

    python perform_sad.py --speech 0.250 --nonspeech 0.100 \
                          -L label_dir rec1.wav rec2.wav rec3.wav ...

Tips
----
- If the corpus you wish to segment is exceptionally large, consider running
  in multithreaded mode by setting ``-j n``, where ``n`` is some positive
  integer. This will instruct the segmenter to partition the input recordings
  into ``n`` sets, and run on the sets in parallel.
- If your recordings are particularly sparse, you may wish to alter to
  reweight the acoustic likelihoods so that speech segments are emphasized
  relative to non-speech segments. To do this, use the ``-a`` flag, which
  controls the scaling factor applied to speech model acoustic likelihoods
  (default is 1).

References
----------
Pitt, M. A., Dilley, L., Johnson, K., Kiesling, S., Raymond, W., Hume, E.,
  and  Fosler-Lussier, E. (2007). Buckeye corpus of conversational speech (2nd
  release). Columbus, OH: Department of Psychology, Ohio State University.
  http://buckeyecorpus.osu.edu/
"""
import argparse
from dataclasses import dataclass
from math import log
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from joblib import delayed, Parallel
import numpy as np

from seglib import __version__ as VERSION
from seglib.io import read_label_file, read_script_file, write_label_file
from seglib.logging import getLogger
from seglib.utils import (concat_segs, convert_to_wav, elim_short_segs,
                          get_dur, merge_segs)

logger = getLogger()


@dataclass
class HTKConfig:
    """TODO"""
    phone_net_path: Path
    macros_path: Path
    hmmdefs_path: Path
    config_path: Path
    dict_path: Path
    monophones_path: Path


def _segment_chunk(audio_path, channel, start, end, htk_config):
    """Segment audio file."""
    audio_path = Path(audio_path)

    # Create directory to hold intermediate segmentations.
    tmp_dir = Path(tempfile.mkdtemp())

    # Convert to WAV and trim on selected channel.
    uri = audio_path.stem
    wav_path = Path(tmp_dir, uri + '.wav')
    convert_to_wav(wav_path, audio_path, channel, start, end)

    # Segment.
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
        lab_path = Path(tmp_dir, uri + '.lab')
        segs = read_label_file(lab_path, in_sec=False)
    except IOError:
        raise IOError
    finally:
        shutil.rmtree(tmp_dir)

    return segs


def _segment_file(audio_path, lab_path, htk_config, channel, min_speech_dur=0.500,
                  min_nonspeech_dur=0.300, min_chunk_dur=10.0,
                  max_chunk_dur=3600.):
    """Perform speech activity detection on a single audio file.

    The resulting segmentation will be saved in an HTK label file in
    ``lab_dir`` with the same name as ``audio_path`` but file extension ``ext``.
    For instance, ``segment_file('A.wav', 'results', '.lab', htk_config)``
    will create a file ``results/A.lab`` containing the segmentation.

    Parameters
    ----------
    audio_path : Path
        Path to audio file on which SAD is to be run.

    lab_path : Path
        Path to output label file.

    htk_config : HTKConfig
        HTK configuration.

    channel : int
        Channel (1-indexed) to perform SAD on.

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
    """
    audio_path = Path(audio_path)
    lab_path = Path(lab_path)

    # Split recording into chunks of at most 3000 seconds.
    rec_dur = get_dur(audio_path)
    if rec_dur > max_chunk_dur:
        bounds = list(np.arange(0, rec_dur, max_chunk_dur))
    else:
        bounds = [0.0, rec_dur]
    suffix_dur = rec_dur - bounds[-1]
    if suffix_dur > 0:
        if suffix_dur < min_chunk_dur:
            bounds[-1] = rec_dur
        else:
            bounds.append(rec_dur)
    rec_bounds = list(zip(bounds[:-1], bounds[1:]))

    # Segment chunks.
    seg_seqs = []
    for rec_onset, rec_offset in rec_bounds:
        segs = _segment_chunk(audio_path, channel, rec_onset, rec_offset,
                              htk_config)
        dur = rec_offset - rec_onset
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

    # Write.
    write_label_file(lab_path, segs)


def segment_file(uri, audio_path, lab_dir, ext, htk_config, channel,
                 min_speech_dur=0.500, min_nonspeech_dur=0.300,
                 min_chunk_dur=10.0, max_chunk_dur=3600.):
    """Perform speech activity detection on a single audio file.

    The resulting segmentation will be saved in an HTK label file in
    ``lab_dir`` with the same name as ``audio_path`` but file extension ``ext``.
    For instance, ``segment_file('A.wav', 'results', '.lab', htk_config)``
    will create a file ``results/A.lab`` containing the segmentation.

    Parameters
    ----------
    uri : str
        Uniform resource identifier (URI) for audio file.

    audio_path : Path
        Path to audio file on which SAD is to be run.

    lab_dir : Path
        Path to output directory for label file.

    ext : str
        File extension to use for label file.

    htk_config : HTKConfig
        HTK configuration.

    channel : int
        Channel (1-indexed) to perform SAD on.

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
    """
    audio_path = Path(audio_path)
    lab_dir = Path(lab_dir)
    lab_path = Path(lab_dir, audio_path.stem + ext)
    rec_dur = get_dur(audio_path)
    max_chunk_dur = min(max_chunk_dur, rec_dur)
    min_chunk_dur = min(min_chunk_dur, rec_dur)
    while max_chunk_dur >= min_chunk_dur:
        try:
            logger.info(
                f'Attempting segmentation for "{audio_path}" with max chunk duration'
                f' of {max_chunk_dur:.2f} seconds')
            _segment_file(
                audio_path, lab_path, htk_config, channel, min_speech_dur,
                min_nonspeech_dur, min_chunk_dur, max_chunk_dur)
            return
        except IOError:
            max_chunk_dur /= 2.
    logger.warning(f'SAD failed for {audio_path}. Skipping.')
    return


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
    old_hmm_defs_path = Path(old_hmmdefs_path)
    new_hmmdefs_path = Path(new_hmmdefs_path)

    with open(old_hmmdefs_path, 'r', encoding='utf-8') as f:
        lines = [line for line in f]

    with open(new_hmmdefs_path, 'w', encoding='utf-8') as g:
        # Header.
        for line in lines[:3]:
            g.write(line)

        # Model definitions.
        curr_phone = None
        for line in lines[3:]:
            # Keep track of which model we are dealing with.
            if line.startswith('~h'):
                curr_phone = line[3:].strip('\"\n')
            # Modify GCONST only for mixtures of speech models.
            if line.startswith('<GCONST>') and curr_phone != 'nonspeech':
                gconst = float(line[9:-1])
                gconst += log(speech_scale_factor)
                line = f'<GCONST> {gconst:.6e}\n'
            g.write(line)


def main():
    script_dir = Path(__file__).parent

    # Parse command line args.
    parser = argparse.ArgumentParser(
        description='Perform speech activity detection on audio files.',
        add_help=True,
        usage='%(prog)s [options] [afs]')
    parser.add_argument(
        'audio_path', metavar='audio-path', type=Path, nargs='*',
        help='audio files to be processed')
    parser.add_argument(
        '-S', metavar='PATH', type=Path, dest='scp_path',
        help='set script file (Default: %(default)s)')
    parser.add_argument(
        '-L', metavar='PATH', type=Path, dest='lab_dir', default=Path.cwd(),
        help="set output label dir (Default: %(default)s)")
    parser.add_argument(
        '-X', nargs=None, default='.lab', metavar='STR', dest='ext',
        help="set output label file extension (Default: %(default)s)")
    parser.add_argument(
        '-a', nargs=None, default=1., type=float, metavar='FLOAT',
        dest='speech_scale_factor',
        help='set speech scale factor. This factor post-multiplies the speech '
             'model acoustic likelihoods. (Default: %(default)s)')
    parser.add_argument(
        '--speech', nargs=None, default=0.500, type=float, metavar='FLOAT',
        dest='min_speech_dur',
        help='set min speech dur in seconds (Default: %(default)s)')
    parser.add_argument(
        '--nonspeech', nargs=None, default=0.300, type=float, metavar='FLOAT',
        dest='min_nonspeech_dur',
        help='set min nonspeech duration in seconds (Default: %(default)s)')
    parser.add_argument(
        '--channel', nargs=None, default=1, type=int, metavar='INT',
        dest='channel',
        help='channel (1-indexed) to use (Default: %(default)s)')
    parser.add_argument(
        '-j', nargs=None, default=1, type=int, metavar='INT', dest='n_jobs',
        help='set num threads to use (Default: %(default)s)')
    parser.add_argument(
        '--version', action='version', version='%(prog)s ' + VERSION)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    # Load paths from script file.
    if args.scp_path is not None:
        audio_paths = read_script_file(args.scp_path)
    elif args.audio_path:
        audio_paths = {audio_path.name : audio_path for audio_path in args.audio_path}
    else:
        return
    n_jobs = min(len(audio_paths), args.n_jobs)

    # Modify GMM weights to account for speech scale factor.
    old_hmmdefs_path = Path(script_dir, 'model', 'hmmdefs')
    new_hmmdefs_path = Path(tempfile.mktemp())
    write_hmmdefs(old_hmmdefs_path, new_hmmdefs_path, args.speech_scale_factor)

    # Perform SAD on files in parallel.
    htk_config = HTKConfig(Path(script_dir, 'model', 'phone_net'),
                           Path(script_dir, 'model', 'macros'),
                           new_hmmdefs_path,
                           Path(script_dir, 'model', 'config'),
                           Path(script_dir, 'model', 'dict'),
                           Path(script_dir, 'model', 'monophones'))
    def kwargs_gen():
        for uri in sorted(audio_paths.keys()):
            audio_path = audio_paths[uri]
            yield dict(
                uri=uri, audio_path=audio_path, lab_dir=args.lab_dir, ext=args.ext,
                htk_config=htk_config, channel=args.channel,
                min_speech_dur=args.min_speech_dur,
                min_nonspeech_dur=args.min_nonspeech_dur)
    f = delayed(segment_file)
    Parallel(n_jobs=n_jobs, verbose=0)(f(**kwargs) for kwargs in kwargs_gen())

    # Remove temporary hmmdefs file.
    new_hmmdefs_path.unlink()


if __name__ == '__main__':
    main()
