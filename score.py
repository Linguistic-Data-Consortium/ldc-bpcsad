#!/usr/bin/env python
# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Score output of SAD system.

To evaluate system output stored in label files ``rec1.lab``, ``rec2.lab``,
``rec3.lab``, ... against corresponding reference label files stored in
``ref_lab_dir``:

    python score.py ref_lab_dir rec1.lab rec2.lab rec3.lab ...

which will
"""
from __future__ import print_function
from __future__ import unicode_literals
import argparse
import os
import sys

import numpy as np

from seglib import __version__ as VERSION
from seglib.io import read_label_file
from seglib.logging import getLogger

logger = getLogger()


def score_file(sys_lf, ref_lab_dir, sys_lab_ext='.lab', ref_lab_ext='.lab',
               step=0.001):
    """Score SAD on a single file.

    Parameters
    ----------
    sys_lf : str
        Path to system label file.

    ref_lab_dir : str
        Path to search for reference label file.

    sys_lab_ext : str, optional
        System label file extension.
        (Default: '.lab')

    ref_lab_ext : str, optional
        Reference label file extension.
        (Default: '.lab')
    
    step : float, optional
        Step size in seconds.
        (Default: 0.001)

    Returns
    -------
    ref_speech_dur : float
        Total speech duration in seconds in reference segmentation.

    ref_nonspeech_dur : float
        Total nonspeech duration in seconds in reference segmentation. 

    fa_dur : float
        Total duration in seconds of system false alarms.

    miss_dur : float
        Total duration in seconds of system misses.
    """
    # NOTE: Would be more proper to use interval trees, but the intervaltree
    #       Python module is in pure Python and far slower than this approach.

    # Load segmentations.
    def try_load_segs(lf):
        try:
            return read_label_file(lf)
        except:
            logger.warning('Problem loading segmentation from %s. Skipping.'
                           % lf)
            return None
    sys_segs = try_load_segs(sys_lf)
    bn = os.path.basename(sys_lf)
    ref_segs = try_load_segs(
        os.path.join(ref_lab_dir, bn.replace(sys_lab_ext, ref_lab_ext)))
    if sys_segs is None or ref_segs is None:
        return

    def to_frames(segs, dur, step=0.001):
        is_speech = np.zeros(int(dur/step), dtype='bool')
        times = np.arange(is_speech.size, dtype='float32')*step
        onsets, offsets, labels = zip(*segs)
        bis = np.searchsorted(times, onsets)
        eis = np.searchsorted(times, offsets)
        for bi, ei, label in zip(bis, eis, labels):
            if label == 'speech':
                is_speech[bi:ei] = True
        return is_speech
    step = 0.01
    dur = min(sys_segs[-1][1], ref_segs[-1][1])
    ref_is_speech = to_frames(ref_segs, dur, step)
    sys_is_speech = to_frames(sys_segs, dur, step)
    ref_speech_dur = np.sum(ref_is_speech)*step
    ref_nonspeech_dur = dur - ref_speech_dur
    fa_dur = np.sum(np.logical_and(~ref_is_speech, sys_is_speech))*step
    miss_dur = np.sum(np.logical_and(ref_is_speech, ~sys_is_speech))*step

    return ref_speech_dur, ref_nonspeech_dur, fa_dur, miss_dur


def score_files(sys_lfs, ref_lab_dir, sys_lab_ext='.lab', ref_lab_ext='.lab'):
    def kwargs_gen():
        for sys_lf in sys_lfs:
            yield dict(sys_lf=sys_lf, ref_lab_dir=ref_lab_dir,
                       sys_lab_ext=sys_lab_ext, ref_lab_ext=ref_lab_ext)
    # DEBUG #
    import time
    t0 = time.time()
    durs = [score_file(**kwargs) for kwargs in kwargs_gen()]
    durs = np.sum(np.row_stack(durs), axis=0)
    ref_speech_dur, ref_nonspeech_dur, fa_dur, miss_dur = durs
    fa_rate = 100*(fa_dur / ref_nonspeech_dur)
    miss_rate = 100*(miss_dur / ref_speech_dur)
    dcf = 0.25*fa_rate + 0.75*miss_rate
    logger.info('DCF: %.2f%%, FA: %.2f%%, MISS: %.2f%%' %
                (dcf, fa_rate, miss_rate))
    dur = time.time() - t0
    print('DUR: %.2f sec' % dur)
    # DEBUG #


if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)

    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description='Score SAD output.', add_help=True,
        usage='%(prog)s [options] ref_lab_dir [sys_lfs]')
    parser.add_argument(
        'ref_lab_dir', nargs=None, help='reference label directory')
    parser.add_argument(
        'sys_lfs', nargs='*', help='system label files to be scored')
    parser.add_argument(
        '-S', nargs=None, default=None, metavar='STR', dest='scpf',
        help='set script file (Default: %(default)s)')
    parser.add_argument(
        '--ref_ext', nargs=None, default='.lab', metavar='STR',
        dest='ref_lab_ext',
        help="set reference label file extension (Default: %(default)s)")
    parser.add_argument(
        '--sys_ext', nargs=None, default='.lab', metavar='STR',
        dest='sys_lab_ext',
        help="set system label file extension (Default: %(default)s)")
    parser.add_argument(
        '--version', action='version', version='%(prog)s ' + VERSION)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    # Load paths from script file.
    if not args.scpf is None:
        with open(args.scpf, 'rb') as f:
            args.sys_lfs = [line.strip() for line in f]

    # Score.
    score_files(args.sys_lfs, args.ref_lab_dir, args.sys_lab_ext,
                args.ref_lab_ext)
