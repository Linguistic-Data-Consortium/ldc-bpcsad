=================================================
    LDC Speech Activity Detector
=================================================

I. Overview
===========
This tool performs speech activity detection (SAD) for audio using a broad
phonetic class (BPC) GMM-HMM recognizer operating on PLP features. Training
was performed using the phonetically transcribed portions of the Buckeye
Corpus with the following mapping of phones to broad phonetic classes:

- *Vowel*: aa, aan, ae, aen, ah, ahn, ao, aon, aw, awn, ay, ayn, eh, ehn, ey,
  eyn, ih, ihn, iy, iyn, ow, own, oy, oyn, uh, uhn, uw, uwn
- *Stop/affricate*: p, t, k, tq, b, d, g, ch, jh, dx, nx
- *Fricative*: f, th, s, sh, v, dh, z, zh, hh
- *Nasal*: em, m, en, n, eng, ng
- *Glide/liquid*: el, l, er, r, w, y
- *Nonspeech*: {bp}, {lg}, {ns}, {sil}, {unk}, {vns}

During feature extraction, frequencies above 4 kHz are ignored, so the
acoustic models are suitable for both wide-band and narrow-band speech.


II. Dependencies
================
The following are required to run this software:

- Python >= 2.7 (https://www.python.org/)
- NumPy >= 1.11.0 (https://github.com/numpy/)
- joblib >= 0.10.0 (https://pypi.python.org/pypi/joblib)
- SoX >= 14.4 (http://sox.sourceforge.net/)
- HTK >= 3.4.0 (http://htk.eng.cam.ac.uk/)

To sucessfully compile HTK, you may need to disable X11 and HSLab
support::

    ./configure --without-x --disable-hslab


III. Performing SAD
===================
To perform SAD for a set of WAV files and store the segmentations in the
directory ``label_dir``::

    python perform_sad.py -L label_dir rec1.wav rec2.wav rec3.wav ...

For each of the WAV files ``rec1.wav``, ``rec2.wav``, ``rec3.wav``, ... a
corresponding label file (``rec1.lab``, ``rec2.lab``, etc) will be created in
``label_dir``. Label files list the detected speech and non-speech segments
with one segment per line, each line having the format::

    ONSET OFFSET LAB

where ``ONSET`` and ``OFFSET`` are the onset and offset of the segment in
seconds and ``LAB`` is one of {speech, nonspeech}. By default these files
will be output with the extension ``.lab``, though this may be changed via the
``-X`` flag.


IV. Converting between output formats
=====================================
To convert label files  ``rec1.lab``, ``rec2.lab``, ``rec3.lab``, ... output
by ``perform_sad.py`` to Praat TextGrids stored in ``tg_dir``::

    python convert_lab.py --format tg -L tg_dir rec1.lab rec2.lab rec3.lab ...

which will create TextGrid files::

    tg_dir/rec1.tg
    tg_dir/rec2.tg
    tg_dir/rec3.tg
    .
    .
    .

In total, four alternate output formats are supported by ``convert_labe.py``::

- ``--format opensad_ref``  --  NIST OpenSAT reference segmentation
- ``--format opensad_sys``  --  NIST OpenSAT system segmentation
- ``--format tdf``  --  Xtrans TDF
- ``--format tg``  --  Praat TextGrid


V. References
=============
- Pitt, M. A., Dilley, L., Johnson, K., Kiesling, S., Raymond, W., Hume, E.,
  and  Fosler-Lussier, E. (2007). Buckeye corpus of conversational speech (2nd
  release). Columbus, OH: Department of Psychology, Ohio State University.
  http://buckeyecorpus.osu.edu/
