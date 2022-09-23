SAD model
=========

Overview
--------

`ldc-bpcsad` performs speech activity detection (SAD) as a byproduct of broad phonetic class (BPC) recognition :cite:`halberstadt1997,scanlon2007,sainath2007,sainath2008`. The speech signal is run through a GMM-HMM based recognizer trained to recognize 5 broad phonetic classes: vowel, stops/affricate, fricative, nasal, and glide/liquid. Each contiguous sequence of BPCs is merged into a single speech segment and this segmentation smoothed to eliminate spurious short pauses. Input features are 13-D PLP features + first and second differences, extracted using a 20-channel filterbank covering 80 Hz to 4 kHz.

The system is implemented using `Hidden Markov Model Toolkit (HTK) <https://htk.eng.cam.ac.uk/>`_ :cite:`htkbook`.



Training
--------

The GMM and HMM transition parameters were trained using the phonetically transcribed portions of `Buckeye Corpus <https://buckeyecorpus.osu.edu/>`_ :cite:`buckeye` with the following mapping from the `Buckeye phoneset <https://buckeyecorpus.osu.edu/BuckeyeCorpusmanual.pdf>`_ to broad phonetic classes:

- ``Vowel``: aa, aan, ae, aen, ah, ahn, ao, aon, aw, awn, ay, ayn, eh, ehn, ey, eyn, ih, ihn, iy, iyn, ow, own, oy, oyn, uh, uhn, uw, uwn
- ``Stop/affricate``: p, t, k, tq, b, d, g, ch, jh, dx, nx
- ``Fricative``: f, th, s, sh, v, dh, z, zh, hh
- ``Nasal``: em, m, en, n, eng, ng
- ``Glide/liquid``: el, l, er, r, w, y

All other sounds were mapped to non-speech. This includes silence and environmental noise as well as non-speech vocalizations such as laughter, breaths, and coughs.



Performance
-----------

Below, we present SAD performance on the `DIHARD III <https://dihardchallenge.github.io/dihard3/>`_ :cite:`dihard3_eval_plan,dihard3_overview` eval set, both overall and by domain:

  .. code-block:: none

    domain                 accuracy    precision    recall     f1    der    dcf    fa rate    miss rate
    -------------------  ----------  -----------  --------  -----  -----  -----  ---------  -----------
    audiobooks                96.02        96.99     97.92  97.45   5.12   4.20      10.55         2.08
    broadcast_interview       94.18        96.49     95.98  96.23   7.52   6.01      11.99         4.02
    clinical                  88.23        90.85     90.01  90.43  19.05  11.15      14.63         9.99
    court                     94.68        96.33     97.31  96.82   6.40   6.58      18.25         2.69
    cts                       94.16        97.83     95.57  96.69   6.55   7.65      17.30         4.43
    maptask                   91.87        91.39     96.46  93.86  12.63   6.77      16.43         3.54
    meeting                   81.53        98.52     78.71  87.51  22.47  17.33       5.46        21.29
    restaurant                57.09        98.46     52.11  68.15  48.70  37.43       6.05        47.89
    socio_field               86.54        97.73     84.61  90.70  17.35  13.24       6.79        15.39
    socio_lab                 90.58        96.37     91.03  93.62  12.40   9.44      10.84         8.97
    webvideo                  76.73        90.49     76.21  82.74  31.80  23.31      21.85        23.79
    OVERALL                   88.52        96.02     89.18  92.48  14.51  11.61      13.98        10.82

For domains containing generally clean recording conditions, high SNR, and low degree of speaker overlap, performance is good with DER generally <10%. In the presence of substantial overlapped speech, low SNR, or challenging environmental conditions, performance degrades. This is particularly noticeable for YouTube recordings (``webvideo`` domain) and speech recorded in restaurants (``restaurant``). In the latter environment, DER rises to nearly 50%. Across all domains, performance is worse than `state-of-the-art <https://github.com/dihardchallenge/dihard3_baseline#sad-scoring>`_ for this test set with deltas ranging from 1.88% DER (broadcast_interview) to 31.56% (restaurant).


Full explanation of table columns:

- ``domain``  --  DIHARD III recording domain; overall results reported under ``OVERALL``
- ``accuracy``  --  % total duration correctly classified
- ``precision``  --  % detected speech that is speech according to the reference segmentation
- ``recall``  --  % speech in the reference segmentation that was detected
- ``f1``  --  F1 (computed from ``precision``/``recall``)
- ``der``  --  detection error rate (DER) :cite:`bredin2017pyannote`
- ``dcf``  --  detection cost function (DCF) :cite:`opensat2018`; weighted function of ``fa rate`` and ``miss rate``
- ``fa rate``  --  % non-speech incorrectly detected as speech
- ``miss rate`` --  % speech that was not detected




References
----------

.. bibliography::
  :filter: docname in docnames
