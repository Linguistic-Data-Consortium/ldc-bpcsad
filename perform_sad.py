#!/usr/bin/env python

import argparse;
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
def segment_file(af, labDir, ext):
    """
    """
    # create tempdir for processing
    tmpDir = tempfile.mkdtemp();

    # convert to 16 kHz wav
    bn = os.path.basename(af);
    uid = os.path.splitext(bn)[0];
    wf = os.path.join(tmpDir, '%s.wav' % uid);

    with open(os.devnull, 'wb') as f:
        cmd = ['sox', af, '-r', '16000', wf];
        subprocess.call(cmd, stdout=f, stderr=f);

    # perform sad
    cmd = ['HVite',
           '-T', '0',
           '-w', os.path.join(scriptDir, 'phone_net'),
           '-l', tmpDir,
           '-H', os.path.join(scriptDir, 'model', 'macros'),
           '-H', os.path.join(scriptDir, 'model', 'hmmdefs'),
           '-C', os.path.join(scriptDir, 'model', 'config'),
           '-p', '-0.3',
           '-s', '5.0',
           '-y', ext,
           os.path.join(scriptDir, 'dict'),
           os.path.join(scriptDir, 'monophones'),
           wf,
           ];
    with open(os.devnull, 'wb') as f:
        subprocess.call(cmd, stdout=f, stderr=f);

    # merge segs
    olf = os.path.join(tmpDir, '%s.%s' % (uid, ext));
    nlf = os.path.join(labDir, '%s.%s' % (uid, ext));

    try:
        segs = read_label_file(olf, inHTKUnits=True);
        segs = merge_segs(segs);
        segs = elim_short_segs(segs, targetLab='nonspch', replaceLab='spch',
                           minDur=args.minNonSpeechDur);
        segs = merge_segs(segs);
        segs = elim_short_segs(segs, targetLab='spch', replaceLab='nonspch',
                               minDur=args.minSpeechDur);
        segs = merge_segs(segs);
        write_label_file(nlf, segs);
    except IOError:
        return af;
    finally:
        shutil.rmtree(tmpDir);


def merge_segs(segs):
    """Merge sequences of segments with same label.
    """
    newSegs = [];
    while len(segs) > 1:
        curr = segs.pop();
        prev = segs.pop();
        if curr[-1] == prev[-1]:
            new = [prev[0], curr[1], curr[-1]];
            segs.append(new);
        else:
            segs.append(prev);
            newSegs.append(curr);
    newSegs.append(segs.pop());
    newSegs.reverse();
    return newSegs;


def elim_short_segs(segs, targetLab='nonspch', replaceLab='spch',
                    minDur=0.300):
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
        if label == targetLab and dur < minDur:
            seg[-1] = replaceLab;
    return segs;


##########################
# Ye olde' main
##########################
if __name__ == '__main__':
    scriptDir = os.path.dirname(__file__);

    # parse command line args
    parser = argparse.ArgumentParser(description='Perform speech activity detection on single-channel audio files.', 
                                     add_help=False,
                                     usage='%(prog)s [options] wfs');
    parser.add_argument('afs', nargs='*',
                        help='audio files to be processed');
    parser.add_argument('-S', nargs='?', default=None,
                        metavar='f', dest='scpPath',
                        help='Set script file (default: none)');
    parser.add_argument('-L', nargs='?', default='./',
                        metavar='dir', dest='labDir',
                        help="Set output label dir (default: current)");
    parser.add_argument('-X', nargs='?', default='lab',
                        metavar='ext', dest='ext',
                        help="Set output label file extension (default: lab)");
    parser.add_argument('--spch', nargs='?', default=0.500, type=float,
                        metavar='tsec', dest='minSpeechDur',
                        help='Set min speech dur (default: 0.5 s)');
    parser.add_argument('--nonspch', nargs='?', default=0.300, type=float,
                        metavar='tsec', dest='minNonSpeechDur',
                        help='Set min nonspeech dur (default: 0.3 s)');
    parser.add_argument('-j', nargs='?', default=1, type=int,
                        metavar='n', dest='maxThreads',
                        help='Set num threads to use (default: 1)');
    args = parser.parse_args();

    if len(sys.argv) == 1:
        parser.print_help();
        sys.exit(1);

    # determine wfs to process
    if args.scpPath:
        with open(args.scpPath, 'r') as f:
            args.afs = [l.strip() for l in f.readlines()];

    # set num threads
    numThreads = min(len(args.afs), args.maxThreads);

    # perform SAD
    res = Parallel(n_jobs=numThreads, verbose=0)(delayed(segment_file)(af, args.labDir, args.ext) for af in args.afs);
    
    # print failures
    failures = [r for r in res if r];
    n = len(res);
    nFail = len(failures);
    nSucc = n - len(failures);
    print('%s out of %s files successfully segmented.' % (nSucc, n));
    if nFail > 0:
        print('There were errors with the following files.');
        for af in failures:
            print(af);
