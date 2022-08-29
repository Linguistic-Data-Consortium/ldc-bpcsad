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
import multiprocessing
from pathlib import Path
import sys

import soundfile as sf
from tqdm import tqdm

from seglib import __version__ as VERSION
from seglib.io import read_script_file, write_label_file
from seglib.logging import getLogger, setup_logger, WARNING
from seglib.segment import segment

logger = getLogger()
setup_logger(logger, level=WARNING)


@dataclass
class Channel:
    """Channel of recording.

    Parameters
    ----------
    uri : str
        Channel URI.

    audio_pat : Path
        Path to audio file channel is one.

    channel : int
        Channel number on audio file (1-indexed).
    """
    uri: str
    audio_path: Path
    channel: int


def parallel_wrapper(channel, args):
    """Wrapper around `segment` for use with multiprocessing."""
    msgs = []  # Warning messages to display to user.
    try:
        with open(channel.audio_path, 'rb') as f:
            x, sr = sf.read(f)
        if x.ndim > 1:
            x = x[:, channel.channel-1]
        segs = segment(
            x, sr, min_speech_dur=args.min_speech_dur,
            min_nonspeech_dur=args.min_nonspeech_dur,
            min_chunk_dur=args.min_chunk_dur, max_chunk_dur=args.max_chunk_dur,
            speech_scale_factor=args.speech_scale_factor)
        lab_path = Path(args.lab_dir, channel.uri + args.ext)
        write_label_file(lab_path, segs)
    except Exception as e:
        print(e)
        msgs.append(f'SAD failed for "{channel.audio_path}". Skipping.')
    return msgs


def main():
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
        audio_paths = {audio_path.stem : audio_path for audio_path in args.audio_path}
    else:
        return
    args.n_jobs = min(len(audio_paths), args.n_jobs)

    # Perform SAD on files in parallel.
    channels = [Channel(uri, audio_path, args.channel)
                for uri, audio_path in audio_paths.items()]
    with multiprocessing.Pool(args.n_jobs) as pool:
        f = partial(parallel_wrapper, args=args)
        with tqdm(total=len(channels), disable=args.disable_progress) as pbar:
            for msgs in pool.imap(f, channels):
                for msg in msgs:
                    logger.warning(msg)
                pbar.update(1)


if __name__ == '__main__':
    main()
