#!/usr/bin/env python

import argparse;
import os;
import sys;

from segs import read_label_file, seconds_2_htk_units;

##########################
# Functions
##########################
def write_htk(segs, lf):
    """
    """
    with open(lf, 'w') as f:
        for onset, offset, label in segs:
            onset = seconds_2_htk_units(onset);
            offset = seconds_2_htk_units(offset);
            f.write('%d %d %s\n' % (onset, offset, label));


def write_tdf(segs, lf):
    with open(lf, 'w') as f:
        # write header
        headerCats = ['file;unicode',
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
        f.write('%s\r\n' % '\t'.join(headerCats));
        f.write(';;MM sectionTypes\t[None, None]\r\n');
        f.write(';;MM sectionBoundaries\t[0.0, 9999999.0]\r\n');

        # write speech segs
        uid = os.path.splitext(os.path.basename(lf))[0];
        nsegs = 0;
        for onset, offset, label in segs:
            if label != 'spch':
                continue;
            nsegs += 1;
            fields = [uid,
                      '1',
                      str(onset),
                      str(offset),
                      'speaker',
                      'NA',
                      'NA',
                      'speech',
                      '0',
                      '0',
                      str(nsegs),
                      '',
                      '',
                     ];
            f.write('%s\r\n' % '\t'.join(fields));
                      
                      
                      
##########################
# Ye olde' main
##########################
if __name__ == '__main__':
    scriptDir = os.path.dirname(__file__);

    # parse command line args
    parser = argparse.ArgumentParser(description='Convert format of SAD output.', 
                                     add_help=False,
                                     usage='%(prog)s [options] lfs');
    parser.add_argument('lfs', nargs='*',
                        help='lab files to be processed');
    parser.add_argument('-S', nargs='?', default=None,
                        metavar='f', dest='scpPath',
                        help='Set script file (default: none)');
    parser.add_argument('-L', nargs='?', default='./',
                        metavar='dir', dest='labDir',
                        help="Set output label dir (default: current)");
    parser.add_argument('-X', nargs='?', default='lab',
                        metavar='ext', dest='ext',
                        help="Set output label file extension (default: lab)");
    parser.add_argument('--format', nargs='?', default='htk',
                        choices = ['htk',
                                   'tdf',
                                  ],
                        metavar='fmt', dest='fmt',
                        help='Set output file formatq (default: %(default)s)');

    args = parser.parse_args();

    if len(sys.argv) == 1:
        parser.print_help();

    # determine wfs
    if args.scpPath:
        with open(args.scpPath, 'r') as f:
            args.lfs = [l.strip() for l in f];

    # process
    for lf in args.lfs:
        segs = read_label_file(lf);
        bn = os.path.basename(lf);
        uid = os.path.splitext(bn)[0];
        nlf = os.path.join(args.labDir, '%s.%s' % (uid, args.ext));
        if args.fmt == 'htk':
            write_htk(segs, nlf);
        elif args.fmt == 'tdf':
            write_tdf(segs, nlf);
