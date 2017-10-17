#!/usr/bin/env python
# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Convert label files output by ``perform_sad.py`` to another format.

To convert a set of label files ``rec1.lab``, ``rec2.lab``, ``rec3.lab``, ...
to the TDF format of Xtrans and store the resultant files in ``tdf_dir``:

    python convert_lab.py --format tdf -L tdf_dir \
                          rec1.lab rec2.lab rec3.lab ...

which will create TDF files:

    tdf_dir/rec1.tdf
    tdf_dir/rec2.tdf
    tdf_dir/rec3.tdf
    .
    .
    .

In total four output formats are supported:

- ``--format opensad_ref``  --  NIST OpenSAT reference segmentation
- ``--format opensad_sys``  --  NIST OpenSAT system segmentation
- ``--format tdf``  --  Xtrans TDF
- ``--format tg``  --  Praat TextGrid

References
----------
- Glenn, M., Lee, H., and Strassel, S.M. (2009). "XTrans: a speech
  annotation and transcription tool." INTERSPEECH
- LDC. (2007). "Using XTrans for broadcast transcription: a user manual."
  https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/xtrans-manual-v3.0.pdf
- NIST. (2015). "Evaluation plan for the NIST open evaluation of speech
  activity detection (OpenSAD15)."
  https://www.nist.gov/sites/default/files/documents/itl/iad/mig/Open_SAD_Eval_Plan_v10.pdf
- Sanders, G. (2015). "NIST OpenSAD scoring software."
  https://www.nist.gov/itl/iad/mig/nist-open-speech-activity-detection-evaluation
"""
from __future__ import print_function
from __future__ import unicode_literals
import argparse
import os
import sys

from joblib import delayed, Parallel

from seglib import __version__ as VERSION
from seglib.io import (read_label_file, write_label_file,
                       write_opensad_reference_file, write_opensad_system_file,
                       write_tdf_file, write_textgrid_file)


FORMAT_TO_EXT = {'opensad_ref' : '_annot.txt',
                 'opensad_sys' : '.txt',
                 'tdf' : '.tdf',
                 'tg' : '.TextGrid'}

FORMAT_TO_WRITE_FN = {'opensad_ref' : write_opensad_reference_file,
                      'opensad_sys' : write_opensad_system_file,
                      'tdf' : write_tdf_file,
                      'tg' : write_textgrid_file}

def convert_label_file(output_dir, lf, fmt):
    """Convert label file to specified formats.

    Allowed formats are:

    - opensad_ref  --  OpenSAD reference file format
    - opensad_sys  --  OpenSAD system file format
    - tdf  --  XTrans TDF format
    - tg  --  Praat TextGrid format

    Parameters
    ----------
    output_dir : str
        Output directory for new file.

    lf : str
        Path to label file to be converted.

    fmt : str
        Format to convet to. Must be one of {'opensad_ref', 'opensad_sys',
        'tdf', 'tg'}.
    """
    ext = FORMAT_TO_EXT[fmt]
    write_fn = FORMAT_TO_WRITE_FN[fmt]
    segs = read_label_file(lf)
    bn = os.path.basename(lf)
    output_fn = os.path.join(output_dir, os.path.splitext(bn)[0] + ext)
    write_fn(output_fn, segs)


if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)

    # Parse command line args.
    parser = argparse.ArgumentParser(
        description='Convert format of SAD output.',
        add_help=False,
        usage='%(prog)s [options] [lfs]')
    parser.add_argument(
        'lfs', nargs='*', help='label files to be processed')
    parser.add_argument(
        '-S', nargs=None, default=None, metavar='STR', dest='scpf',
        help='set script file (Default: %(default)s)')
    parser.add_argument(
        '-L', nargs=None, default='./', metavar='STR', dest='output_dir',
        help='set output directory (Default: %(default)s)')
    parser.add_argument(
        '--format', nargs=None, default='tdf',
        choices = ['opensad_ref',
                   'opensad_sys',
                   'tdf',
                   'tg',
               ],
        metavar='STR',
        help='set output file format (Default: %(default)s)')
    parser.add_argument(
        '-j', nargs=None, default=1, type=int,
        metavar='INT', dest='n_jobs',
        help='set num threads to use (Default: %(default)s)')
    parser.add_argument(
        '--version', action='version', version='%(prog)s ' + VERSION)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    # Load paths from script file.
    if not args.scpf is None:
        with open(args.scpf, 'rb') as f:
            args.lfs = [line.strip() for line in f]

    n_jobs = min(len(args.lfs), args.n_jobs)

    # Convert in parallel.
    f = delayed(convert_label_file)
    def kwargs_gen():
        for lf in args.lfs:
            yield dict(output_dir=args.output_dir, lf=lf, fmt=args.format)
    Parallel(n_jobs=n_jobs, verbose=0)(f(**kwargs) for kwargs in kwargs_gen())
