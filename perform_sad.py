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
from functools import partial
from math import log
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from tqdm import tqdm

from seglib import __version__ as VERSION
from seglib.io import read_label_file, read_script_file, write_label_file
from seglib.logging import getLogger, setup_logger, WARNING
from seglib.utils import (arange, concat_segs, convert_to_wav, elim_short_segs,
                          get_dur, merge_segs)

logger = getLogger()
setup_logger(logger, level=WARNING)


@dataclass
class HTKConfig:
    """TODO"""
    phone_net_path: Path
    macros_path: Path
    hmmdefs_path: Path
    config_path: Path
    dict_path: Path
    monophones_path: Path


@dataclass
class Channel:
    """Channel of recording.

    Parameters
    ----------
    uri : str
        Channel URI.

    rec_uri : str
        Recording URI.

    audio_pat : Path
        Path to audio file channel is one.

    channel : int
        Channel number on audio file (1-indexed).
    """
    uri: str
    audio_path: Path
    channel: int

    @property
    def duration(self):
        """Duration in seconds."""
        return get_dur(self.audio_path)


class SegmentationError(BaseException): pass


def _segment_chunk(channel, onset, offset, htk_config):
    """Segment chunk of channel from audio file."""
    # Create directory to hold intermediate segmentations.
    tmp_dir = Path(tempfile.mkdtemp())

    # Convert to WAV and trim to chunk.
    chunk_uri = f'{channel.uri}_{onset:.3f}_{offset:.3f}'
    wav_path = Path(tmp_dir, chunk_uri + '.wav')
    convert_to_wav(wav_path, channel.audio_path, channel.channel, onset, offset)

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
        lab_path = Path(tmp_dir, chunk_uri + '.lab')
        segs = read_label_file(lab_path, in_sec=False)
    except:
        raise SegmentationError
    finally:
        shutil.rmtree(tmp_dir)

    return segs


def segment_file(channel, htk_config, args):
    """Perform speech activity detection on a single channel of an audio file.

    The resulting segmentation will be saved in an HTK label file in
    ``lab_dir`` with the same name as ``audio_path`` but file extension ``ext``.

    Parameters
    ----------
    channel : Channel
        Audio channel to perform SAD on.

    htk_config : HTKConfig
        HTK configuration.

    args: argparse.Namespace
        Arguments passed via command-line.

    Returns
    -------
    msgs : iterable of str
        Warning messages to pass to user.
    """
    rec_dur = channel.duration  # Duration of recording.
    max_chunk_dur = min(args.max_chunk_dur, channel.duration)
    min_chunk_dur = min(args.min_chunk_dur, channel.duration)
    while max_chunk_dur >= min_chunk_dur:
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
                segs = _segment_chunk(channel, onset, offset, htk_config)
                dur = offset - onset
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
                min_dur=args.min_nonspeech_dur)
            segs = merge_segs(segs)
            segs = elim_short_segs(
                segs, target_lab='speech', replace_lab='nonspeech',
                min_dur=args.min_speech_dur)
            segs = merge_segs(segs)

            # Write.
            lab_path = Path(args.lab_dir, channel.uri + args.ext)
            write_label_file(lab_path, segs)

            return
        except SegmentationError:
            max_chunk_dur /= 2.
    return


def parallel_wrapper(channel, htk_config, args):
    """Wrapper around `segment_file` for use with multiprocessing."""
    msgs = []  # Warning messages to display to user.
    try:
        segment_file(channel, htk_config=htk_config, args=args)
    except:
        msgs.append(f'SAD failed for "{channel.audio_path}". Skipping.')
    return msgs


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
        '--min-chunk-dur', metavar='MIN-CDUR', type=float, default=10,
        help='minimum duration (seconds) of chunks in recursive splitting'
             'procedure; used when HVite fails for full recording '
             '(Default: %(default)s)')
    parser.add_argument(
        '--max-chunk-dur', metavar='MAX-CDUR', type=float, default=3600,
        help='maximum duration (seconds) of chunks in recursive splitting '
             'procedure; used when HVite fails for full recording '
             '(Default: %(default)s)')
    parser.add_argument(
        '--disable-progress', default=False, action='store_true',
        help='disable progress bar')
    parser.add_argument(
        '--n-jobs', '-j', nargs=None, default=1, type=int, metavar='INT',
        dest='n_jobs', help='set num threads to use (Default: %(default)s)')
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
    args.n_jobs = min(len(audio_paths), args.n_jobs)

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
    channels = [Channel(uri, audio_path, args.channel)
                for uri, audio_path in audio_paths.items()]
    with multiprocessing.Pool(args.n_jobs) as pool:
        f = partial(parallel_wrapper, htk_config=htk_config, args=args)
        with tqdm(total=len(channels), disable=args.disable_progress) as pbar:
            for msgs in pool.imap(f, channels):
                for msg in msgs:
                    logger.warning(msg)
                pbar.update(1)

    # Remove temporary hmmdefs file.
    new_hmmdefs_path.unlink()


if __name__ == '__main__':
    main()
