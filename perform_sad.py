#!/usr/bin/env python

import argparse
from math import log
import os
import shutil
import subprocess
import sys
import tempfile

from joblib.parallel import Parallel, delayed
from segs import read_label_file, write_label_file, merge_segs, elim_short_segs


##########################
# Functions
##########################
class HTKConfig(object):
    def __init__(self, phone_net_fn, macros_fn, hmmdefs_fn, config_fn,
                 dict_fn, monophones_fn):

        self.__dict__.update(locals())
        del self.self


def segment_file(af, lab_dir, ext, htk_config):
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

    Returns
    -------
    result : str
        If segmentation is successful then ``result=None``. If it fails then
        ``result=af``.
    """
    # create tempdir for processing
    tmp_dir = tempfile.mkdtemp()

    # convert to 16 kHz wav
    bn = os.path.basename(af)
    uid = os.path.splitext(bn)[0]
    wf = os.path.join(tmp_dir, '%s.wav' % uid)

    with open(os.devnull, 'wb') as f:
        cmd = ['sox', af, '-r', '16000', wf]
        subprocess.call(cmd, stdout=f, stderr=f)

    # perform sad
    cmd = ['HVite',
           '-T', '0',
           '-w', htk_config.phone_net_fn,
           '-l', tmp_dir,
           '-H', htk_config.macros_fn,
           '-H', htk_config.hmmdefs_fn,
           '-C', htk_config.config_fn,
           '-p', '-0.3',
           '-s', '5.0',
           '-y', ext,
           htk_config.dict_fn,
           htk_config.monophones_fn,
           wf,
           ]
    with open(os.devnull, 'wb') as f:
        subprocess.call(cmd, stdout=f, stderr=f)

    # merge segs
    olf = os.path.join(tmp_dir, '%s%s' % (uid, ext))
    nlf = os.path.join(lab_dir, '%s%s' % (uid, ext))

    try:
        segs = read_label_file(olf, in_sec=False)
        segs = merge_segs(segs)
        segs = elim_short_segs(segs, target_lab='nonspch', replace_lab='spch',
                               min_dur=args.min_nonspeech_dur)
        segs = merge_segs(segs)
        segs = elim_short_segs(segs, target_lab='spch', replace_lab='nonspch',
                               min_dur=args.min_speech_dur)
        segs = merge_segs(segs)
        write_label_file(nlf, segs)
    except IOError:
        return af
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
        Path for modified HTK hmmdefs file. If ``newf`` allready exists, it
        will be overwritten.

    speech_scale_factor : float, optional
        Factor by which speech model acoustic likelihoods are scaled prior to
        beam search. Larger values will bias the SAD engine in favour of more
        speech segments.        
        (Default: 1)
    """
    with open(oldf, 'r') as f:
        lines = f.readlines()

    with open(newf, 'w') as g:
        g.writelines(lines[:3]) # header
        curr_phone = None
        for line in lines[3:]:
            # keep track of which model we are dealing with
            if line.startswith('~h'):
                curr_phone = line[3:].strip('\"\n')
            # modify GCONST only for mixtures of speech models
            if line.startswith('<GCONST>') and curr_phone != 'nonspch':
                gconst = float(line[9:-1])
                #print speech_scale_factor
                gconst += log(speech_scale_factor)
                line = '<GCONST> %.6e\n' % gconst
            g.write(line)
                


##########################
# Ye olde' main
##########################
if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)

    # parse command line args
    parser = argparse.ArgumentParser(description='Perform speech activity detection on single-channel audio files.', 
                                     add_help=False,
                                     usage='%(prog)s [options] wfs')
    parser.add_argument('afs', nargs='*',
                        help='audio files to be processed')
    parser.add_argument('-S', nargs='?', default=None,
                        metavar='f', dest='scpf',
                        help='Set script file (default: none)')
    parser.add_argument('-L', nargs='?', default='./',
                        metavar='dir', dest='lab_dir',
                        help="Set output label dir (default: current)")
    parser.add_argument('-X', nargs='?', default='.lab',
                        metavar='ext', dest='ext',
                        help="Set output label file extension (default: .lab)")
    parser.add_argument('-a', nargs='?', default=1, type=float,
                        metavar='k', dest='speech_scale_factor',
                        help='Set speech scale factor. This factor post-multiplies the speech model acoustic likelihoods. (default: 1)')
    parser.add_argument('--spch', nargs='?', default=0.500, type=float,
                        metavar='tsec', dest='min_speech_dur',
                        help='Set min speech dur (default: 0.5 s)')
    parser.add_argument('--nonspch', nargs='?', default=0.300, type=float,
                        metavar='tsec', dest='min_nonspeech_dur',
                        help='Set min nonspeech dur (default: 0.3 s)')
    parser.add_argument('-j', nargs='?', default=1, type=int,
                        metavar='n', dest='n_jobs',
                        help='Set num threads to use (default: 1)')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # determine wfs to process
    if not args.scpf is None:
        with open(args.scpf, 'r') as f:
            args.afs = [l.strip() for l in f.readlines()]

    # set num threads
    n_jobs = min(len(args.afs), args.n_jobs)

    # write temporary hmmdefs file
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
    f = delayed(segment_file)
    res = Parallel(n_jobs=n_jobs, verbose=0)(f(af,
                                               args.lab_dir,
                                               args.ext,
                                               htk_config) for af in args.afs)
    
    # remove temporary hmmdefs file
    os.remove(new_hmmdefs_fn)

    # print failures
    failures = [r for r in res if r]
    n = len(res)
    n_fail = len(failures)
    n_succ = n - len(failures)
    print('%s out of %s files successfully segmented.' % (n_succ, n))
    if n_fail > 0:
        print('There were errors with the following files.')
        for af in failures:
            print(af)
