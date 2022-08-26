# Copyright (c) 2012-2017, Trustees of the University of Pennsylvania
# Authors: nryant@ldc.upenn.edu (Neville Ryant)
# License: BSD 2-clause
"""Functions for reading and writing segmentation formats."""
from pathlib import Path

from .logging import getLogger

__all__ = ['read_label_file', 'write_label_file', 'read_script_file',
           'write_tdf_file', 'write_textgrid_file']


logger = getLogger()


def read_label_file(lf, in_sec=True, enc='utf-8'):
    """Read segmentation from HTK label file.

    Parameters
    ----------
    lf : Path
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
    lf = Path(lf)
    with open(lf, 'r', encoding=enc) as f:
        segs = [line.strip().split()[:3] for line in f]

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
    lf : Path
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
    lf = Path(lf)
    with open(lf, 'w', encoding=enc) as f:
        for onset, offset, label in segs:
            if not in_sec:
                onset = seconds_2_htk_units(onset)
                offset = seconds_2_htk_units(offset)
                line = f'{onset}\t{offset}\t{label}\n'
            else:
                # Fix precision at 2 as tool uses 100 ms sample rate for features.
                line = f'{onset:.2f}\t{offset:.2f}\t{label}\n'
            f.write(line)


def htk_units_2_seconds(t):
    """Convert from 100 ns units to seconds."""
    return t*10.**-7


def seconds_2_htk_units(t):
    """Convert from seconds to 100 ns units."""
    return int(t*10**7)


def write_tdf_file(tdf_path, segs):
    """Write speech segments to file in XTrans TDF format.

    The TDF format is the native XTrans data format and consists of a set of
    records, one per line, each a set of 13 tab delimited fields.

    Parameters
    ----------
    tdf_path : str
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
    tdf_path = Path(tdf_path)
    with open(tdf_path, 'w', encoding='utf-8') as f:
        def write_line(line):
            f.write(line)
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
        uri = tdf_path.stem
        n_segs = 0
        for onset, offset, label in segs:
            if label != 'speech':
                continue
            n_segs += 1
            fields = [uri,
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


def write_textgrid_file(tg_path, segs):
    """Write speech segments to file in Praat TextGrid format.

    The TextGrid format is described in the online Praat manual:

        http://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html

    Parameters
    ----------
    tg_path : Path
        Output TextGrid file.

    segs : list of tuple
        Segments.
    """
    tg_path = tg_path
    with open(tg_path, 'w', encoding='utf-8') as f:
        def write_line(line):
            f.write(line)
            f.write('\n')

        utt_dur = segs[-1][1]

        # Write file and tier headers.
        write_line('File type = "ooTextFile"')
        write_line('Object class = "TextGrid"')
        write_line('')
        write_line('xmin = 0 ')
        write_line(f'xmax = {utt_dur} ')
        write_line('tiers? <exists> ')
        write_line('size = 1 ')
        write_line('item []: ')
        write_line('    item [1]:')
        write_line('        class = "IntervalTier" ')
        write_line('        name = "speech," ')
        write_line('        xmin = 0 ')
        write_line(f'        xmax = {utt_dur} ')
        write_line(f'        intervals: size = {len(segs)} ')

        # Write segments.
        for n, (onset, offset, label) in enumerate(segs):
            write_line(f'        intervals [{n+1}]:')
            write_line(f'            xmin = {onset} ')
            write_line(f'            xmax = {offset} ')
            write_line(f'            text = "{label}" ')
            n += 1


def read_script_file(scp_path):
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
    scp_path : Path
        Path to script file.

    Returns
    -------
    paths : dict
        Mapping from URIs to paths.
    """
    scp_path = Path(scp_path)
    paths = {}
    with open(scp_path, 'r', encoding='utf-8') as f:
        for line in f:
            fields = line.strip().split()
            if len(fields) > 2:
                logger.warn(
                    f'Too many fields in line of script file "{scp_path}".'
                    f'Skipping.')
                continue
            fpath = Path(fields[-1])
            if len(fields) == 2:
                uri = fields[0]
            else:
                uri = fpath.stem
                logger.warn(
                    f'No URI specified for file "{fpath}". '
                    f'Setting using basename: "{uri}".')
            if uri in paths:
                logger.warn(
                    f'Duplicate URI "{uri}" detected. Skipping.')
                continue
            paths[uri] = fpath
    return paths
