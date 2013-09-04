#!/usr/bin/env python

import argparse;
import os;
import sys;

from joblib import Parallel, delayed;

from segs import read_label_file, write_label_file;


##########################
# Functions
##########################
def write_htk(olf, nlf):
    """
    """
    segs = read_label_file(olf);
    write_label_file(nlf, segs, in_sec=False);


def write_tdf(olf, nlf):
    with open(nlf, 'w') as f:
        segs = read_label_file(olf);

        # write header
        header_cats = ['file;unicode',
                      'channel;int',
                      'start;float',
                      'end;float',
                      'speaker;unicode',
                      'speakerType;unicode',
                      'speakerDialect;unicode',
                      'transcript;unicode',
                      'section;int',
                      'turn;int',
                      'segment;int',
                      'sectionType;unicode',
                      'suType;unicode',
                     ];
        f.write('%s\r\n' % '\t'.join(header_cats));
        f.write(';;MM sectionTypes\t[None, None]\r\n');
        f.write(';;MM sectionBoundaries\t[0.0, 9999999.0]\r\n');

        # write speech segs
        uid = os.path.splitext(os.path.basename(nlf))[0];
        nsegs = 0;
        for onset, offset, label in segs:
            if label != 'spch':
                continue;
            nsegs += 1;
            fields = [uid,
                      '0',
                      str(onset),
                      str(offset),
                      'speaker',
                      'NA',
                      'NA',
                      'speech',
                      '0',
                      '0',
                      str(nsegs-1),
                      '',
                      '',
                     ];
            f.write('%s\r\n' % '\t'.join(fields));
                      
                      
def write_tg(olf, nlf):
    """
    """
    with open(nlf, 'w') as f:
        segs = read_label_file(olf);
        utt_dur = segs[-1][1];

        # write file and tier headers
        f.write('File type = "ooTextFile"\n');
        f.write('Object class = "TextGrid"\n');
        f.write('\n');
        f.write('xmin = 0 \n');
        f.write('xmax = %f \n' % utt_dur);
        f.write('tiers? <exists> \n');
        f.write('size = 1 \n');
        f.write('item []: \n');
        f.write('    item [1]:\n');
        f.write('        class = "IntervalTier" \n');
        f.write('        name = "speech," \n');
        f.write('        xmin = 0 \n');
        f.write('        xmax = %f \n' % utt_dur);
        f.write('        intervals: size = %d \n' % len(segs));

        n = 1;
        for onset, offset, label in segs:
            f.write('        intervals [%d]:\n' % n);
            f.write('            xmin = %f \n' % onset);
            f.write('            xmax = %f \n' % offset);
            f.write('            text = "%s" \n' % label);
            n += 1;


##########################
# Ye olde' main
##########################
if __name__ == '__main__':
    script_dir = os.path.dirname(__file__);

    # parse command line args
    parser = argparse.ArgumentParser(description='Convert format of SAD output.', 
                                     add_help=False,
                                     usage='%(prog)s [options] lfs');
    parser.add_argument('lfs', nargs='*',
                        help='lab files to be processed');
    parser.add_argument('-S', nargs='?', default=None,
                        metavar='f', dest='scpf',
                        help='Set script file (default: none)');
    parser.add_argument('-L', nargs='?', default='./',
                        metavar='dir', dest='lab_dir',
                        help="Set output label dir (default: current)");
    parser.add_argument('-X', nargs='?', default='lab',
                        metavar='ext', dest='ext',
                        help="Set output label file extension (default: lab)");
    parser.add_argument('--format', nargs='?', default='htk',
                        choices = ['htk',
                                   'tdf',
                                   'tg',
                                  ],
                        metavar='fmt', dest='fmt',
                        help='Set output file format (default: %(default)s)');
    parser.add_argument('-j', nargs='?', default=1, type=int,
                        metavar='n', dest='n_jobs',
                        help='Set num threads to use (default: 1)');
    args = parser.parse_args();

    if len(sys.argv) == 1:
        parser.print_help();
        sys.exit(1);

    # determine lfs
    if not args.scpf is None:
        with open(args.scpf, 'r') as f:
            args.lfs = [l.strip() for l in f];

    # determine label files
    bns = [os.path.basename(lf) for lf in args.lfs];
    uids = [os.path.splitext(bn)[0] for bn in bns];
    nlfs = [os.path.join(args.lab_dir, '%s.%s' % (uid, args.ext)) for uid in uids];

    # set num threads                                                           
    n_jobs = min(len(args.lfs), args.n_jobs);

    # process
    if args.fmt == 'htk':
        f = delayed(write_htk);
    elif args.fmt == 'tdf':
        f = delayed(write_tdf);
    elif args.fmt == 'tg':
        f = delayed(write_tg);
    Parallel(n_jobs=n_jobs, verbose=0)(f(args.lfs[ii], 
                                         nlfs[ii]) for ii in xrange(len(nlfs)));
