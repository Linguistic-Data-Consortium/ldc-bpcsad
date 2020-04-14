# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for reading and writing segmentation formats."""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import os

from .logging import getLogger

__all__ = ['read_label_file', 'write_label_file', 'read_script_file',
           'write_opensad_reference_file', 'write_opensad_system_file',
           'write_tdf_file', 'write_textgrid_file']


logger = getLogger()


def read_label_file(lf, in_sec=True, enc='utf-8'):
    """Read segmentation from HTK label file.

    Parameters
    ----------
    lf : str
        Path to label file.

    in_sec : bool, optional
        If True then onsets/offsets in ``lf`` are assumed to be in seconds. If
        False they are assumed to be in HTK 100 ns units.
        (Default: True)

    enc : str, optional
        Character encoding of ``lf``.
        (Default: 'utf-8')

    Returns
    -------
    segs : list of tuple
        List of segments, each expressed as a tuple
        (``onset``, ``offset``, ``label``), where ``onset`` and ``offset`` are
        the onset and offset of the segment in seconds relative to the start
        of the recording.
    """
    with open(lf, 'rb') as f:
        segs = [line.decode(enc).strip().split()[:3] for line in f]

    for seg in segs:
        seg[0] = float(seg[0])
        seg[1] = float(seg[1])
        if not in_sec:
            seg[0] = htk_units_2_seconds(seg[0])
            seg[1] = htk_units_2_seconds(seg[1])

    return segs


def write_label_file(lf, segs, in_sec=True, enc='utf-8'):
    """Write segmentation to HTK label file.

    Parameters
    ----------
    lf : str
        Path to label file.

    segs : list of tuple
        List of segments, each expressed as a tuple
        (``onset``, ``offset``, ``label``), where ``onset`` and ``offset`` are
        the onset and offset of the segment in seconds relative to the start
        of the recording.

    in_sec : bool, optional
        If True then write onsets and offsets in terms of seconds. If False
        then write in terms of HTK 100 ns units.
        (Default: True)

    enc : str, optional
        Character encoding of ``lf``.
        (Default: 'utf-8')
    """
    with open(lf, 'wb') as f:
        for onset, offset, label in segs:
            if not in_sec:
                onset = seconds_2_htk_units(onset)
                offset = seconds_2_htk_units(offset)
                line = '%d %d %s\n' % (onset, offset, label)
            else:
                line = '%.2f %.2f %s\n' % (onset, offset, label)
            f.write(line.encode(enc))


def htk_units_2_seconds(t):
    """Convert from 100 ns units to seconds.
    """
    return t*10.**-7


def seconds_2_htk_units(t):
    """Convert from seconds to 100 ns units, rounded down to nearest integer.
    """
    return int(t*10**7)


def write_opensad_system_file(fn, segs, test_set='test_set'):
    """Write segments to file in SYSTEM format expected by NIST OpenSAD eval
    tool.

    The output file is in the SAD system format expected by the OpenSAD eval
    script ``scoreFile_SAD.pl`` as documented in the OpenSAD eval plan
    (Figure 3).

    Parameters
    ----------
    fn : str
        Output OpenSAD SYSTEM file.

    segs : list of tuple
        Segments.

    test_set : str, optional
        Test set ID. This goes into column 2 of the NIST OpenSAD file.
        (Default: 'test_set')

    References
    ----------
    - NIST. (2015). "Evaluation plan for the NIST open evaluation of speech
      activity detection (OpenSAD15)."
      https://www.nist.gov/sites/default/files/documents/itl/iad/mig/Open_SAD_Eval_Plan_v10.pdf
    - Sanders, G. (2015). "NIST OpenSAD scoring software."
      https://www.nist.gov/itl/iad/mig/nist-open-speech-activity-detection-evaluation
    """
    with open(fn, 'wb') as f:
        bn = os.path.basename(fn)
        fid = os.path.splitext(bn)[0]
        for onset, offset, label in segs:
            label = 'non-speech' if label == 'nonspeech' else label
            cols = ['fake_testDef.xml', # Test Definition File.
                    test_set, # TestSet ID.
                    'test', # Test ID.
                    'SAD', # Task.
                    fid, # File ID.
                    '%.3f' % onset, # Interval start (seconds).
                    '%.3f' % offset, # Interval end (seconds).
                    label, # Type (one of {speech, non-speech}).
                    '0.5', # Confidence.
            ]
            line = '\t'.join(cols)
            f.write(line.encode('utf-8'))
            f.write('\n')


def write_opensad_reference_file(fn, segs, test_set='test_set'):
    """Write segments to file in REFERENCE format expected by NIST OpenSAD eval
    tool.

    The output file is in the SAD reference format expected by the OpenSAD eval
    script ``scoreFile_SAD.pl`` as documented in the OpenSAD eval plan
    (Figure 4).

    Parameters
    ----------
    fn : str
        Output OpenSAD REFERENCE file.

    segs : list of tuple
        Segments.

    test_set : str, optional
        Test set ID. This goes into column 2 of the NIST OpenSAD file.
        (Default: 'test_set')

    References
    ----------
    - NIST. (2015). "Evaluation plan for the NIST open evaluation of speech
      activity detection (OpenSAD15)."
      https://www.nist.gov/sites/default/files/documents/itl/iad/mig/Open_SAD_Eval_Plan_v10.pdf
    - Sanders, G. (2015). "NIST OpenSAD scoring software."
      https://www.nist.gov/itl/iad/mig/nist-open-speech-activity-detection-evaluation
    """
    with open(fn, 'wb') as f:
        bn = os.path.basename(fn)
        fid = os.path.splitext(bn)[0]
        for onset, offset, label in segs:
            label = 'NS' if label == 'nonspeech' else 'S'
            cols = ['fake_testDef.xml', # Audio filename.
                    '1', # Channel ID.
                    '%.3f' % onset, # Interval start (seconds).
                    '%.3f' % offset, # Interval end (seconds).
                    label, # Type (one of {S, NS, T}).
                    'manual', # Confidence.
            ]
            cols.extend(['']*6)
            line = '\t'.join(cols)
            f.write(line.encode('utf-8'))
            f.write('\n')


def write_tdf_file(tdf_fn, segs):
    """Write speech segments to file in XTrans TDF format.

    The TDF format is the native XTrans data format and consists of a set of
    records, one per line, each a set of 13 tab delimited fields.

    Parameters
    ----------
    tdf_fn : str
        Output TDF file.

    segs : list of tuple
        Segments.

    References
    ----------
    - Glenn, M., Lee, H., and Strassel, S.M. (2009). "XTrans: a speech
      annotation and transcription tool." INTERSPEECH
    - LDC. (2007). "Using XTrans for broadcast transcription: a user manual."
      https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/xtrans-manual-v3.0.pdf
    """
    with open(tdf_fn, 'wb') as f:
        def write_line(line):
            f.write(line.encode('utf-8'))
            f.write('\r\n') # This is what Xtrans does...

        # Write header.
        col_names = ['file;unicode', # File name.
                     'channel;int', # Audio channel.
                     'start;float', # Onset of segment in seconds.
                     'end;float', # Offset of segment in seconds.
                     'speaker:unicode', # Speaker name or id.
                     'speakerType:unicode', # Speaker type.
                     'speakerDialect:unicode', # Speaker dialect.
                     'transcript:unicode', # Transcript.
                     'section:int', # Section id.
                     'turn:int', # Turn id.
                     'segment:int', # Segment id.
                     'sectionType:unicode', # Section type.
                     'suType:unicode', # SU type.
                    ]
        write_line('\t'.join(col_names))
        write_line('MM sectionTypes\t[None, None]')
        write_line('MM sectionBoundaries\t[0.0, 9999999.0]')

        # Write speech segments.
        fid = os.path.splitext(os.path.basename(tdf_fn))[0]
        n_segs = 0
        for onset, offset, label in segs:
            if label != 'speech':
                continue
            n_segs += 1
            fields = [fid,
                      '0',
                      str(onset),
                      str(offset),
                      'speaker',
                      'NA',
                      'NA',
                      'speech',
                      '0',
                      '0',
                      str(n_segs-1),
                      '',
                      '',
                     ]
            write_line('\t'.join(fields))


def write_textgrid_file(tgf, segs):
    """Write speech segments to file in Praat TextGrid format.

    The TextGrid format is described in the online Praat manual:

        http://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html

    Parameters
    ----------
    tgf : str
        Output TextGrid file.

    segs : list of tuple
        Segments.
    """
    with open(tgf, 'wb') as f:
        def write_line(line):
            f.write(line.encode('utf-8'))
            f.write('\n')

        utt_dur = segs[-1][1]

        # Write file and tier headers.
        write_line('File type = "ooTextFile"')
        write_line('Object class = "TextGrid"')
        write_line('')
        write_line('xmin = 0 ')
        write_line('xmax = %f ' % utt_dur)
        write_line('tiers? <exists> ')
        write_line('size = 1 ')
        write_line('item []: ')
        write_line('    item [1]:')
        write_line('        class = "IntervalTier" ')
        write_line('        name = "speech," ')
        write_line('        xmin = 0 ')
        write_line('        xmax = %f ' % utt_dur)
        write_line('        intervals: size = %d ' % len(segs))

        # Write segments.
        for n, (onset, offset, label) in enumerate(segs):
            write_line('        intervals [%d]:' % (n + 1))
            write_line('            xmin = %f ' % onset)
            write_line('            xmax = %f ' % offset)
            write_line('            text = "%s" ' % label)
            n += 1


def read_script_file(fn):
    """Read Kaldi or HTK script file.

    The script file is expected to be in one of two formats:

    - Kaldi

      Each line contains has two whitespace delimited fields:

      - uri  --  a uniform resource identifier for the file
      - path  --  the path to the file

    - HTK

      Each line consists of a file path.

    For HTK format script files, URIs will be deduced automatically from the
    file's basename.

    Parameters
    ----------
    fn : str
        Path to script file.

    Returns
    -------
    paths : dict
        Mapping from URIs to paths.
    """
    paths = {}
    with open(fn, 'rb') as f:
        for line in f:
            fields = line.decode('utf-8').strip().split()
            if len(fields) > 2:
                logger.warning(
                    'Too many fields in line of script file "%s". Skipping.',
                    fn)
                continue
            fpath = fields[-1]
            if len(fields) == 2:
                uri = fields[0]
            else:
                uri = os.path.basename(fpath).split('.')[0]
                logger.warning(
                    'No URI specified for file "%s". '
                    'Setting using basename: "%s".', fpath, uri)
            if uri in paths:
                logger.warning(
                    'Duplicate URI "%s" detected. Skipping.', uri)
                continue
            paths[uri] = fpath
    return paths
