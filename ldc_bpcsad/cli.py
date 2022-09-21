#!/usr/bin/env python
# Copyright (c) 2012-2022, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Perform speech activity detection (SAD) using a GMM-HMM broad phonetic class recognizer."""
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
from ldc_bpcsad.decode import decode
from ldc_bpcsad.io import (write_audacity_label_file, write_htk_label_file,
                           write_rttm_file, write_textgrid_file)
from ldc_bpcsad.logging import getLogger, setup_logger, DEBUG, WARNING
from ldc_bpcsad.utils import which

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
        rec_dur = len(x) / sr
        kwargs = {'is_sorted' : True, 'precision' : 2}
        if args.output_fmt == 'htk':
            write_htk_label_file(
                Path(args.output_dir, channel.uri + '.lab'),
                segs, rec_dur=rec_dur, **kwargs)
        elif args.output_fmt == 'audacity':
            write_audacity_label_file(
                Path(args.output_dir, channel.uri + '.txt'),
                segs, rec_dur=rec_dur, **kwargs)
        elif args.output_fmt == 'rttm':
            write_rttm_file(
                Path(args.output_dir, channel.uri + '.rttm'),
                segs, file_id=channel.audio_path.stem,
                channel=channel.channel, **kwargs)
        elif args.output_fmt == 'textgrid':
            write_textgrid_file(
                Path(args.output_dir, channel.uri + '.TextGrid'),
                segs, tier='sad', rec_dur=rec_dur, **kwargs)
    except Exception as e:
        msgs.append(f'SAD failed for "{channel.audio_path}". Skipping.')
    return msgs


def get_parser():
    """Return `argparse.ArgumentParser`."""
    parser = argparse.ArgumentParser(
        description='Perform speech activity detection on audio files.',
        add_help=True)
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
        '--output-dir', metavar='OUTPUT-DIR', type=Path, dest='output_dir',
        default=Path.cwd(),
        help="output segmentations to OUTPUT-DIR (Default: current directory)")
    parser.add_argument(
        '--output-fmt', metavar='FMT', default='htk',
        choices=['audacity', 'htk', 'rttm', 'textgrid'],
        help='output file format (Default: %(default)s)')
    parser.add_argument(
        '--speech', metavar='SPEECH-DUR', default=0.500, type=float,
        dest='min_speech_dur',
        help='filter speech segments shorter than SPEECH-DUR seconds '
             '(Default: %(default)s)')
    parser.add_argument(
        '--nonspeech', metavar='NONSPEECH-DUR', default=0.300, type=float,
        dest='min_nonspeech_dur',
        help='merge speech segments separated by less than NONSPEECH-DUR '
             'seconds (Default: %(default)s)')
    parser.add_argument(
        '--speech-scale-factor', metavar='SPEECH-SCALE', default=1.,
        type=float,
        help='post-multiply speech model acoustic likelihoods by '
             'SPEECH-SCALE (Default: %(default)s)')
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
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    # Set up logger.
    log_level = DEBUG if args.debug else WARNING
    setup_logger(logger, level=log_level)

    # Ensure HTK is installed.
    if not which('HVite'):
        # TODO: Update link when docs are online.
        logger.error(
            'HVite is not installed. Please install HTK and try again: '
            '[INSERT LINK TO INSTRUCTIONS HERE]')
        sys.exit(1)

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
    args.output_dir.mkdir(parents=True, exist_ok=True)
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
