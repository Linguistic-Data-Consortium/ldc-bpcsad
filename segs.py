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
