SAD model
=========

`ldc-bpcsad` performs speech activity detection by decoding the audio into a sequence of [broad phonetic classes `BPC <https://ieeexplore.ieee.org/abstract/document/4100697>`_ using a GMM-HMM recognizer operating on narrowband PLP features. The SAD engine was trained using the phonetically transcribed portions of `Buckeye Corpus <https://buckeyecorpus.osu.edu/>`_ and the following mapping of phones to broad phonetic classes:

- Vowel: aa, aan, ae, aen, ah, ahn, ao, aon, aw, awn, ay, ayn, eh, ehn, ey, eyn, ih, ihn, iy, iyn, ow, own, oy, oyn, uh, uhn, uw, uwn
- Stop/affricate: p, t, k, tq, b, d, g, ch, jh, dx, nx
- Fricative: f, th, s, sh, v, dh, z, zh, hh
- Nasal: em, m, en, n, eng, ng
- Glide/liquid: el, l, er, r, w, y
- Nonspeech: {bp}, {lg}, {ns}, {sil}, {unk}, {vns}


