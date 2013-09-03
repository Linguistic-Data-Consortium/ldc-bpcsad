#!/usr/bin/env python

import argparse;
from math import log;
import os;
import shutil;
import subprocess;
import sys;
import tempfile;

from joblib.parallel import Parallel, delayed;
from segs import read_label_file, write_label_file;


##########################
# Functions
##########################
def segment_file(af, lab_dir, ext):
    """
    """
    # create tempdir for processing
    tmp_dir = tempfile.mkdtemp();

    # convert to 16 kHz wav
    bn = os.path.basename(af);
    uid = os.path.splitext(bn)[0];
    wf = os.path.join(tmp_dir, '%s.wav' % uid);

    with open(os.devnull, 'wb') as f:
        cmd = ['sox', af, '-r', '16000', wf];
        subprocess.call(cmd, stdout=f, stderr=f);

    # perform sad
    cmd = ['HVite',
           '-T', '0',
           '-w', os.path.join(script_dir, 'phone_net'),
           '-l', tmp_dir,
           '-H', os.path.join(script_dir, 'model', 'macros'),
           '-H', os.path.join(script_dir, 'model', 'hmmdefs_temp'),
           '-C', os.path.join(script_dir, 'model', 'config'),
           '-p', '-0.3',
           '-s', '5.0',
           '-y', ext,
           os.path.join(script_dir, 'dict'),
           os.path.join(script_dir, 'monophones'),
           wf,
           ];
    with open(os.devnull, 'wb') as f:
        subprocess.call(cmd, stdout=f, stderr=f);

    # merge segs
    olf = os.path.join(tmp_dir, '%s.%s' % (uid, ext));
    nlf = os.path.join(lab_dir, '%s.%s' % (uid, ext));

    try:
        segs = read_label_file(olf, in_sec=False);
        segs = merge_segs(segs);
        segs = elim_short_segs(segs, target_lab='nonspch', replace_lab='spch',
                               min_dur=args.min_nonspeech_dur);
        segs = merge_segs(segs);
        segs = elim_short_segs(segs, target_lab='spch', replace_lab='nonspch',
                               min_dur=args.min_speech_dur);
        segs = merge_segs(segs);
        write_label_file(nlf, segs);
    except IOError:
        return af;
    finally:
        shutil.rmtree(tmp_dir);


def write_hmmdefs(oldf, newf, speech_scale_factor=1):
    """
    """
    with open(oldf, 'r') as f:
        lines = f.readlines();

    with open(newf, 'w') as g:
        g.writelines(lines[:3]); # header
        curr_phone = None;
        for line in lines[3:]:
            # keep track of which model we are dealing with
            if line.startswith('~h'):
                curr_phone = line[3:].strip('\"\n');
            # modify GCONST only for mixtures of speech models
            if line.startswith('<GCONST>') and curr_phone != 'nonspch':
                gconst = float(line[9:-1]);
                #print speech_scale_factor;
                gconst += log(speech_scale_factor);
                line = '<GCONST> %.6e\n' % gconst;
            g.write(line);
                

def merge_segs(segs):
    """Merge sequences of segments with same label.
    """
    new_segs = [];
    while len(segs) > 1:
        curr = segs.pop();
        prev = segs.pop();
        if curr[-1] == prev[-1]:
            new = [prev[0], curr[1], curr[-1]];
            segs.append(new);
        else:
            segs.append(prev);
            new_segs.append(curr);
    new_segs.append(segs.pop());
    new_segs.reverse();
    return new_segs;


def elim_short_segs(segs, target_lab='nonspch', replace_lab='spch',
                    min_dur=0.300):
    """Convert nonspeech segments below specified duration to
    speech.

    Inputs:
        segs:

        targetLab:

        replaceLab:

        minDur:    cutoff to reognize nonspeech seg.
                   (default: 0.300 [NIST standard])
    """
    for seg in segs:
        onset, offset, label = seg;
        dur = offset - onset;
        if label == target_lab and dur < min_dur:
            seg[-1] = replace_lab;
    return segs;


##########################
# Ye olde' main
##########################
if __name__ == '__main__':
    script_dir = os.path.dirname(__file__);

    # parse command line args
    parser = argparse.ArgumentParser(description='Perform speech activity detection on single-channel audio files.', 
                                     add_help=False,
                                     usage='%(prog)s [options] wfs');
    parser.add_argument('afs', nargs='*',
                        help='audio files to be processed');
    parser.add_argument('-S', nargs='?', default=None,
                        metavar='f', dest='scpf',
                        help='Set script file (default: none)');
    parser.add_argument('-L', nargs='?', default='./',
                        metavar='dir', dest='lab_dir',
                        help="Set output label dir (default: current)");
    parser.add_argument('-X', nargs='?', default='lab',
                        metavar='ext', dest='ext',
                        help="Set output label file extension (default: lab)");
    parser.add_argument('-a', nargs='?', default=1, type=float,
                        metavar='k', dest='speech_scale_factor',
                        help='Set speech scale factor. This factor post-multiplies the speech model acoustic likelihoods. (default: 1)');
    parser.add_argument('--spch', nargs='?', default=0.500, type=float,
                        metavar='tsec', dest='min_speech_dur',
                        help='Set min speech dur (default: 0.5 s)');
    parser.add_argument('--nonspch', nargs='?', default=0.300, type=float,
                        metavar='tsec', dest='min_nonspeech_dur',
                        help='Set min nonspeech dur (default: 0.3 s)');
    parser.add_argument('-j', nargs='?', default=1, type=int,
                        metavar='n', dest='n_jobs',
                        help='Set num threads to use (default: 1)');
    args = parser.parse_args();

    if len(sys.argv) == 1:
        parser.print_help();
        sys.exit(1);

    # determine wfs to process
    if not args.scpf is None:
        with open(args.scpf, 'r') as f:
            args.afs = [l.strip() for l in f.readlines()];

    # set num threads
    n_jobs = min(len(args.afs), args.n_jobs);

    # write temporary hmmdefs file
    old_hmmdefs = os.path.join(script_dir, 'model', 'hmmdefs');
    new_hmmdefs = os.path.join(script_dir, 'model', 'hmmdefs_temp');
    write_hmmdefs(old_hmmdefs, new_hmmdefs, args.speech_scale_factor);

    # perform SAD
    f = delayed(segment_file);
    res = Parallel(n_jobs=n_jobs, verbose=0)(f(af, args.lab_dir, args.ext) for af in args.afs);
    
    # remove temporary hmmdefs file
    os.remove(new_hmmdefs);

    # print failures
    failures = [r for r in res if r];
    n = len(res);
    n_fail = len(failures);
    n_succ = n - len(failures);
    print('%s out of %s files successfully segmented.' % (n_succ, n));
    if n_fail > 0:
        print('There were errors with the following files.');
        for af in failures:
            print(af);
