*****************
Command-line tool
*****************

.. contents:: Table of Contents
  :depth: 2

     

Basic usage
===========

The easiest way to perform speech activity detection (SAD) for a set of audio files is via the :ref:`ldc-bpcsad` command line tool. To perform SAD for channel 1 of each of a set of audio files ``rec1.flac``, ``rec2.flac``, ``rec3.flac``, ... and output their segmentation as HTK label files under the directory ``label_dir``:

  .. code-block:: console

    ldc-bpcsad --channel 1 --output-dir label_dir rec1.flac rec2.flac rec3.flac ...

This will result in one label file for input file (e.g., ``rec1.lab``, ``rec2.lab``, ...), each of the form:

  .. code-block:: none

    0.00 1.05 nonspeech
    1.05 3.55 speech
    3.55 4.65 nonspeech
    .
    .
    .


Script files
============

It is also possible to specify the audio files and channels to be processed using a script file specified via the ``--scp`` flag. Currently, two script file formats are supported:

- ``htk`` --  :ref:`HTK script file<htk_scp>` (**default**)
- ``json``  --  :ref:`JSON script file<json_scp>`


.. _htk_scp:

HTK script file
---------------

If ``--scp-fmt htk`` is specified, :ref:`ldc-bpcsad` will load the audio files to be segmented from an `HTK <https://ai.stanford.edu/~amaas/data/htkbook.pdf>`_ script file. An HTK script file consists of a list of file paths, one path per line; e.g.:

  .. code-block:: none

    /path/to/rec1.flac
    /path/to/rec2.flac
    /path/to/rec3.flac

For instance, if ``task.scp`` is the above HTK script file, then:

  .. code-block:: console

    ldc-bpcsad --channel 1 --output-dir label_dir --scp-fmt htk --scp task.scp

is equivalent to:

  .. code-block:: console

    ldc-bpcsad --channel 1 --output-dir label_dir /path/to/rec1.flac /path/to/rec2.flac /path/to/rec3.flac


.. _json_scp:

JSON script file
----------------

If ``--scp-fmt json`` is specified, :ref:`ldc-bpcsad` will load the audio files **AND** channels to be segmented from a JSON file. The JSON file should consist of a sequence of JSON objects, each containing the following three key-value pairs:

- ``audio_path``  --  Path to audio file to perform SAD on.
- ``channel``  --  Channel number of audio file to perform SAD on (1-indexed).
- ``uri``  --  Basename for output file containing SAD result.

E.g.:

  .. code-block:: json

    [{
        "uri": "rec1_c1",
        "audio_path": "/path/to/rec1.flac",
        "channel": 1
    }, {
        "uri": "rec1_c2",
        "audio_path": "/path/to/rec1.flac",
        "channel": 2
    }, {
        "uri": "rec2_c1",
        "audio_path": "/path/to/rec2.flac",
        "channel": 1
    }]

For instance, if ``task.json`` is the above JSON file, then:

  .. code-block:: console

    ldc-bpcsad --output-dir label_dir --scp-fmt json --scp task.json

will output the following three HTK label files to ``label_dir``:

- ``rec1_c1.lab``  --  result of SAD for channel 1 of ``rec1.flac``
- ``rec1_c2.lab``  --  result of SAD for channel 2 of ``rec1.flac``
- ``rec2_c1.lab``  --  result of SAD for channel 1 of ``rec2.flac``

.. note::

   When using a JSON script file, the ``--channel`` flag has no effect.



Output formats
==============

The output file format for SAD output can be specified via the ``--output-fmt`` flag. Currently, four options are available:

- ``htk`` --  :ref:`HTK label file<htk_lab>` (**default**)
- ``rttm``  --  :ref:`Rich Transcription Time Marked (RTTM) file<rttm>`
- ``audacity``  --  :ref:`Audacity label file<audacity>`
- ``textgrid``  --  :ref:`Praat TextGrid<textgrid>`


.. _htk_lab:

HTK label file
--------------
If ``--output-fmt htk`` is specified, SAD output will be stored as `HTK <https://ai.stanford.edu/~amaas/data/htkbook.pdf>`_ label files. Each label file contains one segment per line, each line having the form:

  .. code-block:: none

    <ONSET>\t<OFFSET>\t<LABEL>

where:

- ``ONSET``  --  onset of segment in seconds from beginning of recording
- ``OFFSET``  --  offset of segment in seconds from beginning of recording
- ``LABEL``  --  segment label; either "speech" or "nonspeech"


The segments are stored in order with the following guarantees:

- the onset of the first segment is always 0
- the offset of the final segment is always equal to the recording duration
- the offset of segment ``n`` equals the onset of segment ``n+1``.

E.g.:

  .. code-block:: none

    0.00 1.05 nonspeech
    1.05 3.55 speech
    3.55 4.65 nonspeech


.. _rttm:

RTTM file
---------
If ``--output-fmt rttm`` is specified, SAD output will be stored  as `Rich Transcription Time Marked (RTTM) files <https://web.archive.org/web/20100606092041if_/http://www.itl.nist.gov/iad/mig/tests/rt/2009/docs/rt09-meeting-eval-plan-v2.pdf>`_. Each RTTM file contains one speech segment per line, with each line having the form:

  .. code-block:: none

     SPEAKER <FILE-ID> <CHANNEL> <ONSET> <DURATION> <NA> <NA> speaker <NA> <NA>

where:

- ``FILE-ID``  --  file name; the basename of the audio file that the turn is on, minus extension (e.g., ``rec1_a``)
- ``CHANNEL``  --  the channel number of the turn on the audio file (1-indexed)
- ``ONSET``  --  onset of turn in seconds from beginning of recording
- ``DURATION``  --  duration of turn in seconds

E.g.:

  ..  code-block:: none

    SPEAKER rec1 1 1.05 2.50 <NA> <NA> speaker <NA> <NA>
    SPEAKER rec1 1 4.00 3.31 <NA> <NA> speaker <NA> <NA>
    SPEAKER rec1 1 10.11 4.15 <NA> <NA> speaker <NA> <NA>


.. _audacity:

Audacity label file
-------------------
If ``--output-fmt audacity`` is specified, SAD output will be stored as `Audacity label files <https://manual.audacityteam.org/man/importing_and_exporting_labels.html#Standard_.28default.29_format>`_ . As we are not using any of the optional features of this file forma (e.g., frequency ranges), the resulting files are **exactly identical** to the :ref:`HTK label files<htk_lab>` previously described and this is functionally an alias for ``--output-fmt htk`` except with a different file extension (HTK: ``.lab``, Audacity: ``.txt``).


.. _textgrid:

Praat TextGrid
--------------
If ``--output-fmt textgrid`` is specified, SAD output will be stored as `Praat TextGrid files <https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html>`_. Each TextGrid file will contain a single IntervalTier named ``sad``, consisting of a sequence of intervals whose attributes should be interpreted as follows:

- ``xmin``  --  onset of segment in seconds from beginning of recording
- ``xmax``  --  offset of segment in seconds from beginning of recording
- ``text`` --  segment label; either "speech" or "nonspeech"

E.g.:

  .. code-block:: none

    File type = "ooTextFile"
    Object class = "TextGrid"

    xmin = 0
    xmax = 4.65
    tiers? <exists>
    size = 1
    item []:
        item [1]:
            class = "IntervalTier"
            name = "sad"
            xmin = 0
            xmax = 5.0
            intervals: size = 3
            intervals [1]:
                xmin = 0
                xmax = 1.05
                text = "non-speech"
            intervals [2]:
                xmin = 1.05
                xmax = 3.55
                text = "speech"
            intervals [3]:
                xmin = 3.55
                xmax = 4.65
                text = "non-speech"


Postprocessing
==============

By default :ref:`ldc-bpcsad` postprocesses it's output to eliminate speech segments less than 500 ms in duration and nonspeech segments less than 300 ms in duration. While these defaults are suitable for SAD that is being done as a precursor to transcription by human annotators, they may be overly restrictive for other uses. If necessary, the minimum speech and nonspeech segment durations may be changed via the ``--speech`` and ``--nonspeech`` flags. For instance, to instead use minimum durations of 250 ms for speech and 100 ms for nonspeech:

  .. code-block:: console

    ldc-bpcsad --channel 1 --output-dir label_dir --speech 0.250 --nonspeech 0.100 rec1.flac rec2.flac rec3.flac



.. _audio


Audio formats
=============
This section describes the default supported input audio file formats. As audio IO is handled by the `soundfile <https://github.com/bastibe/python-soundfile>`_ Python package, additional formats may be supported depending on your installed version of `soundfile <https://github.com/bastibe/python-soundfile>`_. To see if additional formats are supported, run:

  .. code-block:: console

    ldc-bpcsad -h

and check the ``audio file formats`` list at the end of the help message.

.. TODO: Add MP3 once soundfile updates

**Supported formats:**

- ``.aiff``, ``.aif``  --  AIFF (Apple/SGI)
- ``.au``, ``.snd``  --  AU (Sun/NeXT)
- ``.avr``  --  AVR (Audio Visual Research)
- ``.caf``  --  CAF (Apple Core Audio File)
- ``.flac``  --  FLAC (Free Lossless Audio Codec)
- ``.htk``  --  HTK (HMM Tool Kit)
- ``.iff`` -- IFF (Amiga IFF/SVX8/SV16)
- ``.mat``, ``.mat4``, ``.mat5``  -- Matlab 4.2/5.0 (GNU Octave 2.0/2.1)
- ``.mpc``  --  Musepack MPC (Akai MPC 2k)
- ``.ogg``, ``.vorbis``  --  OGG Vorbis compressed audio
- ``.paf``, ``.fap``  --  Ensoniq PARIS file format
- ``.pvf``  --  PVF (Portable Voice Format)
- ``.rf64``  --  EBU RF64 enhancement of MBWF
- ``.sd2``  --  Sound Designer 2 format
- ``.sds``  --  MIDI Sample Dump Standard
- ``.sf``  --  IRCAM SDIF (Institut de Recherche et Coordination Acoustique/Musique Sound Description Interchange Format)
- ``.sph``, ``.nist``, ``.wav``  --  NIST SPEHERE formatl SHORTEN compression is not supported
- ``.voc``  --  Sound Blaster VOC files
- ``.w64``  --  Sonic Foundry 64-bit RIFF/WAV format
- ``.wav``  --  Microsoft .WAV RIFF format
- ``.wve``  --  Psion 8-bit A-law
- ``.xi``  --  Fasttracker 2 Extended Instrument format.





.. _ldc-bpcsad:

Usage
=====

.. argparse::
   :module: ldc_bpcsad.cli
   :func: get_parser
   :prog: ldc-bpcsad
