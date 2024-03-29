#!/usr/bin/env python3
# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
"""Perform speech activity detection.

Speech acticity detection (SAD) is performed using a broad phonetic class
recognizer.
"""
import argparse
from dataclasses import dataclass
from functools import partial
import json
import multiprocessing
import multiprocessing.dummy
from pathlib import Path
import sys
from typing import List

import soundfile as sf
from soundfile import LibsndfileError, SoundFileError
from tqdm import tqdm

from ldc_bpcsad import __version__ as VERSION
from ldc_bpcsad.decode import decode
from ldc_bpcsad.io import (write_audacity_label_file, write_htk_label_file,
                           write_rttm_file, write_textgrid_file)
from ldc_bpcsad.logging import getLogger, setup_logger, DEBUG, WARNING
from ldc_bpcsad.utils import get_nframes_wav, which


logger = getLogger()


class ChannelNotFoundError(Exception):
    """Raised when a channel doesn't exist."""
    pass


class FileEmptyError(Exception):
    """Raised when a file contains no data."""
    pass


@dataclass
class Channel:
    """Channel of recording.

    Parameters
    ----------
    id : str
        Unique identifier of channel. Used to name output file containing SAD
        output.

    audio_path : Path
        Path to audio file channel is on.

    channel : int
        Channel number on audio file (1-indexed).

    Attributes
    ----------
    format : str
        Audio format (derived from extension).
    """
    id: str
    audio_path: Path
    channel: int

    def __post_init__(self):
        self.audio_path = Path(self.audio_path)
        self.channel = int(self.channel)
        self.format = self.audio_path.suffix.lstrip('.').upper()

    def validate(self):
        """Check that channel is valid.

        If all checks pass, return the channel. Otherwise, raises an exception.
        """
        # Check that file exists.
        if not self.audio_path.exists():
            raise FileNotFoundError(
                f'Audio file does not exist: {self.audio_path}')

        # Check that file is not empty.
        n_bytes = self.audio_path.lstat().st_size
        if n_bytes == 0:
            raise FileEmptyError('File contains no data.')

        # Check in a known audio format.
        if self.format not in sf._formats:
            raise SoundFileError(f'Unknown format "{self.format}"')

        # Check that soundfile can, in actuality, read it  --  the header is a
        # lie, etc.
        info = sf.info(self.audio_path, verbose=True)
        logger.debug(f'Source audio file: {info}')
        logger.debug('')
        logger.debug(f'Source channel: {self.channel}.')
        logger.debug('')

        # Check that file does not consists of JUST a header.
        if info.frames == 0 or info.frames == 9223372036854775807:
            # soundfile.info seems to encounter an underflow errors for some
            # formats when file is empty.
            raise FileEmptyError('File contains no data.')

        # Check that # frames indicated in header agrees with actual # frames.
        # Currently only implemented for WAV.
        if self.format == 'WAV':
            try:
                n_frames_header = get_nframes_wav(self.audio_path)
                n_frames_actual = info.frames
                if n_frames_header != n_frames_actual:
                    logger.warning(
                        f'Header frame count wrong for file '
                        f'"{self.audio_path}": '
                        f'{n_frames_header} != {n_frames_actual}')
            except Exception as e:
                # Bare except, yes, yes. yada, yada, yada/
                pass

        # Check that channel EXISTS on file.
        if not 1 <= self.channel <= info.channels:
            raise ChannelNotFoundError(
                f'Invalid source channel: {self.channel}. Source '
                f'channel be positive integer <= {info.channels}.')

        return self


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
            channel_id = audio_path.stem
            chan = Channel(channel_id, audio_path, channel)
            channels.append(chan)
    return channels


def load_json_script_file(fpath):
    """Read channels to process from JSON file.

    The JSON file should consist of a sequence of JSON objects, each containing
    the following three key-value pairs:

    - ``channel_id``  --  Unique identifier of channel. Used to name output
      file containing SAD output.
    - ``audio_path``  --  Path to audio file that the channel is on.
    - ``channel``  --  Channel number of audio file to process (1-indexed).

    For instance:

        ```json
        [{
            "channel_id": "rec1_c1",
            "audio_path": "/path/to/rec1.flac",
            "channel": 1
        }, {
            "channel_id": "rec1_c2",
            "audio_path": "/path/to/rec1.flac",
            "channel": 2
        }, {
            "channel_id": "rec2_c1",
            "audio_path": "/path/to/rec2.flac",
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
                record['channel_id'], Path(record['audio_path']),
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


# Mapping from output formats to corresponding extensions.
OUTPUT_EXTS = {'htk': '.lab',
               'audacity': '.txt',
               'rttm': '.rttm',
               'textgrid': '.TextGrid'}


@dataclass
class CompletedProcess:
    """Return value from `parallel_wrapper`, representing a process that has
    completed.

    Parameters
    ----------
    channel : Channel
        Channel SAD was attempted on.

    success : bool
        Did processing succeed for the channel.
    """
    channel: Channel
    success: bool


def _process_one_file(channel, args):
    """Process one file."""
    success = False
    try:
        logger.debug('#' * 72)
        logger.debug('Attempting SAD.')
        logger.debug('#' * 72)

        # Basic validation of channel.
        channel.validate()

        # Perform SAD.
        with open(channel.audio_path, 'rb') as f:
            x, sr = sf.read(f)
        if x.ndim > 1:
            x = x[:, channel.channel - 1]
        segs = decode(
            x, sr, min_speech_dur=args.min_speech_dur,
            min_nonspeech_dur=args.min_nonspeech_dur,
            speech_scale_factor=args.speech_scale_factor,
            silent=False)
        
        # Write to output file.
        rec_dur = len(x) / sr
        kwargs = {'is_sorted': True, 'precision': 2}
        ext = OUTPUT_EXTS[args.output_fmt]
        output_path = Path(args.output_dir, channel.id + ext)
        logger.debug(f'Saving SAD to "{output_path}".')
        logger.debug(f'Output file format: {args.output_fmt}')
        if args.output_fmt == 'htk':
            write_htk_label_file(
                output_path, segs, rec_dur=rec_dur, **kwargs)
        elif args.output_fmt == 'audacity':
            write_audacity_label_file(
                output_path, segs, rec_dur=rec_dur, **kwargs)
        elif args.output_fmt == 'rttm':
            write_rttm_file(
                output_path, segs, file_id=channel.audio_path.stem,
                channel=channel.channel, **kwargs)
        elif args.output_fmt == 'textgrid':
            write_textgrid_file(
                output_path, segs, tier='sad', rec_dur=rec_dur, **kwargs)

        success = True
    except LibsndfileError as e:
        logger.debug(e, exc_info=True)
        msg = str(e)
        if (msg.endswith('unknown format.') or
            msg.endswith('unimplemented format.') or
            msg.endswith('Format not recognised.')):
            # If unknown/unsupported file format, remind users what formats
            # are supported.
            logger.debug('To see supported formats, run:')
            logger.debug('')
            logger.debug('    ldc-bpcsad --help')
    except Exception as e:
        logger.debug(e, exc_info=True)

    return CompletedProcess(channel, success)


def process_one_file(channel, args):
    """Process one file."""
    p = _process_one_file(channel, args)
    if not p.success:
        logger.warning(
            f'SAD failed for channel {p.channel.channel} of '
            f'"{p.channel.audio_path}". Skipping. For more details rerun with '
            f'the --debug flag.')


def get_parser():
    """Return `argparse.ArgumentParser`."""
    audio_formats = ', '.join(sorted(sf.available_formats().values()))
    parser = argparse.ArgumentParser(
        description='Perform speech activity detection on audio files.',
        epilog=f'audio file formats: {audio_formats}',
        add_help=True)
    parser.add_argument(
        'audio_path', metavar='audio-path', type=Path, nargs='*',
        help='audio files to be processed')
    parser.add_argument(
        '--channel', default=1, type=int, metavar='CHAN',
        dest='channel',
        help='channel (1-indexed) to process on each audio file '
             '(Default: %(default)s)')
    parser.add_argument(
        '--scp', metavar='SCP', type=Path,
        dest='scp_path',
        help='path to script file (Default: %(default)s)')
    parser.add_argument(
        '--scp-fmt', metavar='SCP-FMT', dest='scp_fmt', default='htk',
        choices=['htk', 'json'],
        help='script file format (Default: %(default)s)')
    parser.add_argument(
        '--output-dir', metavar='OUTPUT-DIR', type=Path, dest='output_dir',
        default=Path.cwd(),
        help="output segmentations to OUTPUT-DIR (Default: current directory)")
    parser.add_argument(
        '--output-fmt', metavar='OUTPUT-FMT', default='htk',
        choices=sorted(OUTPUT_EXTS.keys()),
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
        parser.exit()
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

    # Load channels.
    if args.scp_path:
        if args.scp_fmt == 'htk':
            channels = load_htk_script_file(
                args.scp_path, channel=args.channel)
        elif args.scp_fmt == 'json':
            channels = load_json_script_file(args.scp_path)
        else:
            assert False
    else:
        channels = []
        for audio_path in args.audio_path:
            channels.append(Channel(audio_path.stem, audio_path, args.channel))
    # TODO: Check for dupes.
    if not channels:
        return

    # Perform SAD on files in parallel.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.n_jobs = min(args.n_jobs, len(channels))
    logger.debug(f'COMMAND LINE CALL: {" ".join(sys.argv)}')
    if args.debug:
        logger.debug(
            'Flag "--n-jobs" is ignored for debug mode. Using single-threaded '
            'implementation.')
        args.n_jobs = 1
        logger.debug('Progress bar is disabled for debug mode.')
        logger.debug('')
        args.disable_progress = True
    Pool = multiprocessing.Pool
    if args.n_jobs == 1:
        Pool = multiprocessing.dummy.Pool
    with Pool(args.n_jobs) as pool:
        f = partial(process_one_file, args=args)
        with tqdm(total=len(channels), disable=args.disable_progress) as pbar:
            for res in pool.imap(f, channels):
                pbar.update(1)


if __name__ == '__main__':
    main()
