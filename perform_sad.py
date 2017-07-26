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
- For very long recordings (on the order of an hour or longer), Viterbi
  decoding may fail. If this happens, the best solution is to manually split
  the recording into  two or more shorter files, each less than an hour in
  length.

References
----------
Pitt, M. A., Dilley, L., Johnson, K., Kiesling, S., Raymond, W., Hume, E.,
  and  Fosler-Lussier, E. (2007). Buckeye corpus of conversational speech (2nd
  release). Columbus, OH: Department of Psychology, Ohio State University.
  http://buckeyecorpus.osu.edu/
"""
from __future__ import print_function
from __future__ import unicode_literals
import argparse
from math import log
import os
import shutil
import subprocess
import sys
import tempfile

from joblib.parallel import delayed, Parallel

from seglib.io import read_label_file, write_label_file
from seglib.logging import getLogger
from seglib.utils import elim_short_segs, merge_segs

logger = getLogger()


class HTKConfig(object):
    def __init__(self, phone_net_fn, macros_fn, hmmdefs_fn, config_fn,
                 dict_fn, monophones_fn):
        self.__dict__.update(locals())
        del self.self


def segment_file(af, lab_dir, ext, htk_config, channel):
    """Perform speech activity detection on a single audio file.

    The resulting segmentation will be saved in an HTK label file in
    ``lab_dir`` with the same name as ``af`` but file extension ``ext``.
    For instance, ``segment_file('A.wav', 'results', '.lab', htk_config)``
    will create a file ``results/A.lab`` containing the segmentation.

    Parameters
    ----------
    af : str
        Path to audio file on which SAD is to be run.

    lab_dir : str
        Path to output directory for label file.

    ext : str
        File extension to use for label file.

    htk_config : HTKConfig
        HTK configuration.

    channel : int
        Channel (1-indexed) to perform SAD on.
    """
    # Create directory to hold intermediate segmentations.
    tmp_dir = tempfile.mkdtemp()

    # Convert to 16 kHz monochannel WAV using SoX.
    bn = os.path.basename(af)
    uid = os.path.splitext(bn)[0]
    wf = os.path.join(tmp_dir, '%s.wav' % uid)
    with open(os.devnull, 'wb') as f:
        cmd = ['sox', af,
               '-r', '16000', # Resample to 16 kHz.
                '-b', '16', # Make 16-bit.
               '-e', 'signed-integer', # Linear PCM.
               '-t', 'wav', # Write wav header.
               wf,
               'remix', str(channel), # Keep single channel.
               ]
        subprocess.call(cmd, stdout=f, stderr=f)

    # Perform SAD using HTK. This command both extracts the features and
    # performs decoding.
    cmd = ['HVite',
           '-T', '0',
           '-w', htk_config.phone_net_fn,
           '-l', tmp_dir,
           '-H', htk_config.macros_fn,
           '-H', htk_config.hmmdefs_fn,
           '-C', htk_config.config_fn,
           '-p', '-0.3',
           '-s', '5.0',
           '-y', ext.lstrip('.'),
           htk_config.dict_fn,
           htk_config.monophones_fn,
           wf,
           ]
    with open(os.devnull, 'wb') as f:
        subprocess.call(cmd, stdout=f, stderr=f)

    # Merge segments.
    olf = os.path.join(tmp_dir, '%s%s' % (uid, ext))
    nlf = os.path.join(lab_dir, '%s%s' % (uid, ext))
    try:
        segs = read_label_file(olf, in_sec=False)
        segs = merge_segs(segs)
        segs = elim_short_segs(
            segs, target_lab='nonspeech', replace_lab='speech',
            min_dur=args.min_nonspeech_dur)
        segs = merge_segs(segs)
        segs = elim_short_segs(
            segs, target_lab='speech', replace_lab='nonspeech',
            min_dur=args.min_speech_dur)
        segs = merge_segs(segs)
        write_label_file(nlf, segs)
    except IOError:
        logger.warn('SAD failed for %s. Skipping.' % af)
    finally:
        shutil.rmtree(tmp_dir)


def write_hmmdefs(oldf, newf, speech_scale_factor=1):
    """Modify an HTK hmmdefs file in which speech model acoustic likelihoods
    are scaled by ``speech_scale_factor``.

    Parameters
    ----------
    oldf : str
        Path to original HTK hmmdefs file.

    newf : str
        Path for modified HTK hmmdefs file. If ``newf`` already exists, it
        will be overwritten.

    speech_scale_factor : float, optional
        Factor by which speech model acoustic likelihoods are scaled prior to
        beam search. Larger values will bias the SAD engine in favour of more
        speech segments.
        (Default: 1)
    """
    with open(oldf, 'rb') as f:
        lines = f.readlines()

    with open(newf, 'wb') as g:
        g.writelines(lines[:3]) # Header.
        curr_phone = None
        for line in lines[3:]:
            # Keep track of which model we are dealing with.
            if line.startswith('~h'):
                curr_phone = line[3:].strip('\"\n')
            # Modify GCONST only for mixtures of speech models.
            if line.startswith('<GCONST>') and curr_phone != 'nonspeech':
                gconst = float(line[9:-1])
                gconst += log(speech_scale_factor)
                line = '<GCONST> %.6e\n' % gconst
            g.write(line)



if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)

    # Parse command line args.
    parser = argparse.ArgumentParser(
        description='Perform speech activity detection on audio files.',
        add_help=True,
        usage='%(prog)s [options] [afs]')
    parser.add_argument(
        'afs', nargs='*', help='audio files to be processed')
    parser.add_argument(
        '-S', nargs=None, default=None, metavar='STR', dest='scpf',
        help='set script file (Default: %(default)s)')
    parser.add_argument(
        '-L', nargs=None, default='./', metavar='STR', dest='lab_dir',
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
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    # Load paths from script file.
    if not args.scpf is None:
        with open(args.scpf, 'rb') as f:
            args.afs = [line.strip() for line in f]
        
    n_jobs = min(len(args.afs), args.n_jobs)

    # Modify GMM weights to account for speech scale factor.
    old_hmmdefs_fn = os.path.join(script_dir, 'model', 'hmmdefs')
    new_hmmdefs_fn = tempfile.mktemp()
    write_hmmdefs(old_hmmdefs_fn, new_hmmdefs_fn, args.speech_scale_factor)

    # Perform SAD on files in parallel.
    htk_config = HTKConfig(os.path.join(script_dir, 'phone_net'),
                           os.path.join(script_dir, 'model', 'macros'),
                           new_hmmdefs_fn,
                           os.path.join(script_dir, 'model', 'config'),
                           os.path.join(script_dir, 'dict'),
                           os.path.join(script_dir, 'monophones'))
    kwargs = dict(lab_dir=args.lab_dir, ext=args.ext, htk_config=htk_config,
                  channel=args.channel)
    f = delayed(segment_file)
    Parallel(n_jobs=n_jobs, verbose=0)(f(af, **kwargs) for af in args.afs)

    # Remove temporary hmmdefs file.
    os.remove(new_hmmdefs_fn)
