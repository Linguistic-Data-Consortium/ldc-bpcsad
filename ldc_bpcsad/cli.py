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
import json
import multiprocessing
import multiprocessing.dummy
from pathlib import Path
import sys

import soundfile as sf
from tqdm import tqdm

from ldc_bpcsad import __version__ as VERSION
from ldc_bpcsad.io import write_htk_label_file
from ldc_bpcsad.logging import getLogger, setup_logger, DEBUG, WARNING
from ldc_bpcsad.decode import decode

logger = getLogger()


@dataclass
class Channel:
    """Channel of recording.

    Parameters
    ----------
    uri : str
        Uniform resource identifier (URI) of channel. Used to name output file
        containing SAD output.

    audio_path : Path
        Path to audio file channel is on.

    channel : int
        Channel number on audio file (1-indexed).
    """
    uri: str
    audio_path: Path
    channel: int

    def __post_init__(self):
        self.audio_path = Path(self.audio_path)
        self.channel = int(self.channel)


    def validate(self, log=True):
        """Return True if channel is valid."""
        if not self.audio_path.exists():
            if log:
                logger.warning(
                    f'Audio file does not exist. Skipping. '
                    f'FILE: "{self.audio_path}", CHANNEL: {self.channel}')
            return False
        try:
            info = sf.info(self.audio_path)
        except Exception as e:
            if log:
                logger.warning(
                    f'Problem reading audio file header. Skipping. '
                    f'FILE: "{self.audio_path}", CHANNEL: {self.channel}')
            return False
        if not (1 <= self.channel <= info.channels):
            if log:
                logger.warning(
                    f'Invalid channel. Skipping. '
                    f'FILE: "{self.audio_path}", CHANNEL: {self.channel}')
            return False
        return True


def load_htk_script_file(fpath, channel=1):
    """Read channels to process from HTK script file.

    An HTK script file specifies a set of file paths, each path separated by a
    newline; e.g.:

        /data/flac/rec01.flac
        /data/flac/rec02.flac
        /data/flac/rec03.flac

    Parameters
    ----------
    fpath : Path
        Path to script file.

    channel : int, optional
        Channel number (1-indexed) to perform SAD on for each file.
        (Default: 1)

    Returns
    -------
    list of Channel
        Channels to perform SAD on.
    """
    channels = []
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            audio_path = Path(line.strip())
            uri = audio_path.stem
            chan = Channel(uri, audio_path, channel)
            channels.append(chan)
    return channels


def load_json_script_file(fpath):
    """Read channels to process from JSON file.

    The JSON file should consist of a sequence of JSON objects, each containing
    the following three key-valiue pairs:

    - uri  --  Uniform resource identifier (URI) of channel. Used to name
      output file containing SAD output.
    - audio_path  --  Path to audio file that the channel is on.
    - channel  --  Channel number of audio file to process (1-indexed).

    For instance:

        ```json
        [{
            "uri": "rec01_c1",
            "audio_path": "/data/flac/rec01.flac",
            "channel": 1
        }, {
            "uri": "rec01_c2",
            "audio_path": "/data/flac/rec01.flac",
            "channel": 2
        }, {
            "uri": "rec02_c1",
            "audio_path": "/data/flac/rec02.flac",
            "channel": 1
        }]
        ```

    Parameters
    ----------
    fpath : Path
        Path to script file.

    Returns
    -------
    list of Channel
        Channels to perform SAD on.
    """
    with open(fpath, 'r', encoding='utf-8') as f:
        records = json.load(f)
    channels = []
    for record in records:
        try:
            channel = Channel(
                record['uri'], Path(record['audio_path']),
                int(record['channel']))
        except Exception as e:
            channel = None
        if not channel:
            logger.warning(
                f'Malformed record in JSON script file. Skipping. '
                f'SCRIPT FILE: {fpath}, RECORD: {record}')
            continue
        channels.append(channel)
    return channels


def parallel_wrapper(channel, args):
    """Wrapper around `decode` for use with multiprocessing."""
    # Warning messages are collected and handled in calling process due to
    # potential ugly interactions with multiprocessing and tqdm. This can be
    # avoided at cost of an additional dependency by using the
    # multiprocessing-logging package:
    #
    #     https://github.com/jruere/multiprocessing-logging
    #
    # TODO: Re-evaluate decision to use multiprocessing-logging.
    msgs = []  # Warning messages to display to user.
    try:
        with open(channel.audio_path, 'rb') as f:
            x, sr = sf.read(f)
        if x.ndim > 1:
            x = x[:, channel.channel-1]
        segs = decode(
            x, sr, min_speech_dur=args.min_speech_dur,
            min_nonspeech_dur=args.min_nonspeech_dur,
            speech_scale_factor=args.speech_scale_factor)
        lab_path = Path(args.lab_dir, channel.uri + args.ext)
        rec_dur = len(x) / sr
        write_htk_label_file(lab_path, segs, rec_dur=rec_dur, is_sorted=True)
    except Exception as e:
        msgs.append(f'SAD failed for "{channel.audio_path}". Skipping.')
    return msgs


def main():
    parser = argparse.ArgumentParser(
        description='Perform speech activity detection on audio files.',
        add_help=True,
        usage='%(prog)s [options] [afs]')
    parser.add_argument(
        'audio_path', metavar='audio-path', type=Path, nargs='*',
        help='audio files to be processed')
    parser.add_argument(
        '--htk-scp', metavar='HTK-PATH', type=Path, dest='htk_scp_path',
        help='read audio files from HTK script file HTK-PATH '
             '(Default: %(default)s)')
    parser.add_argument(
        '--channel', nargs=None, default=1, type=int, metavar='CHAN',
        dest='channel',
        help='channel (1-indexed) to process on each audio file '
             '(Default: %(default)s)')
    parser.add_argument(
        '--json-scp', metavar='JSON-PATH', type=Path,
        dest='json_scp_path',
        help='read channels to process from JSON script file JSON-PATH '
             '(Default: %(default)s)')
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
        '--disable-progress', default=False, action='store_true',
        help='disable progress bar')
    parser.add_argument(
        '--debug', default=False, action='store_true',
        help='enable DEBUG mode')
    parser.add_argument(
        '--n-jobs', '-j', nargs=None, default=1, type=int, metavar='INT',
        dest='n_jobs', help='set num threads to use (Default: %(default)s)')
    parser.add_argument(
        '--version', action='version', version='%(prog)s ' + VERSION)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    # Set up logger.
    log_level = DEBUG if args.debug else WARNING
    setup_logger(logger, level=log_level)

    # Load and validate channels.
    # TODO: Check for conflicts.
    if args.htk_scp_path:
        channels = load_htk_script_file(
            args.htk_scp_path, channel=args.channel)
    elif args.json_scp_path:
        channels = load_json_script_file(args.json_scp_path)
    else:
        channels = []
        for audio_path in args.audio_path:
            channels.append(Channel(audio_path.stem, audio_path, args.channel))
    channels = [channel for channel in channels if channel.validate(log=True)]
    # TODO: Check for dupes.
    if not channels:
        return


    # Perform SAD on files in parallel.
    args.lab_dir.mkdir(parents=True, exist_ok=True)
    args.n_jobs = min(args.n_jobs, len(channels))
    if args.debug:
        logger.warning(
            'Flag "--n-jobs" is ignored for debug mode. Using single-threaded '
            'implementation.')
        args.n_jobs = 1
    Pool = multiprocessing.Pool if args.n_jobs > 1 else multiprocessing.dummy.Pool
    with Pool(args.n_jobs) as pool:
        f = partial(parallel_wrapper, args=args)
        with tqdm(total=len(channels), disable=args.disable_progress) as pbar:
            for msgs in pool.imap(f, channels):
                for msg in msgs:
                    logger.warning(msg)
                pbar.update(1)


if __name__ == '__main__':
    main()
