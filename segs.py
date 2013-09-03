def read_label_file(lf, in_sec=True):
    """
    """
    with open(lf, 'r') as f:
        segs = [line.strip().split()[:3] for line in f];


    for seg in segs:
        seg[0] = float(seg[0]);
        seg[1] = float(seg[1]);
        if not in_sec:
            seg[0] = htk_units_2_seconds(seg[0]);
            seg[1] = htk_units_2_seconds(seg[1]);

    return segs;


def write_label_file(fn, segs, in_sec=True):
    """
    """
    with open(fn, 'w') as f:
        for onset, offset, label in segs:
            if not in_sec:
                onset = seconds_2_htk_units(onset);
                offset = seconds_2_htk_units(offset);
            f.write('%.2f %.2f %s\n' % (onset, offset, label));


def htk_units_2_seconds(t):
    """Convert from 100ns units to seconds.
    """
    return t*10.**-7;


def seconds_2_htk_units(t):
    """Convert from seconds to 100ns units, rounded down to nearest integer.
    """
    return int(t*10**7);
