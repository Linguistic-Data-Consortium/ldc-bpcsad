# Copyright (c) 2023, Trustees of the University of Pennsylvania
# See LICENSE for licensing conditions
"""HTK command line tool wrappers."""
from dataclasses import dataclass
from math import log
from pathlib import Path
import subprocess
from subprocess import CalledProcessError
from typing import Iterable

from .utils import which

__all__ = ['HTKError', 'HTKSegfault', 'HViteConfig', 'hvite', 'write_hmmdefs']


@dataclass
class HViteConfig:
    """HVite decoding configuration

    Parameters
    ----------
    slf_path : pathlib.Path
        Path to HTK SLF file defining the recognition network.

    hmmdefs_path : pathlib.Path
        Path to HTK MMF file containing HMM definitions.

    macros_path : pathlib.Path
        Path to HTK MMF file containing additional macro definitions (e.g.,
        variance floors).

    config_path : pathlib.Path
        Path to HTK configuration file defining expected source audio format
        and feature extraction pipeline.

    dict_path : pathlib.Path
        Path to pronunciation dictionary.

    monophones_path : pathlib.Path
        Path to file listing HMMs to load from the MMF files.
    """
    slf_path: Path
    hmmdefs_path: Path
    macros_path: Path
    config_path: Path
    dict_path: Path
    monophones_path: Path

    @staticmethod
    def from_model_dir(model_dir):
        """Construct :ref:`HViteConfig` from contents ofa model directory.

        TODO

        Parameters
        ----------
        model_dir : pathlib.Path
            Model directory.

        Returns
        -------
        HViteConfig
        """
        model_dir = Path(model_dir)
        return HViteConfig(
            model_dir / 'phone_net',
            model_dir / 'hmmdefs',
            model_dir / 'macros',
            model_dir  / 'config',
            model_dir / 'dict',
            model_dir / 'monophones')


class HTKError(Exception):
    """Call to HTK command line tool failed."""


class HTKSegfault(HTKError):
    """Call to HTK command line tool resulted in segmentation fault.."""


def hvite(wav_path, config, working_dir):
    """Perform Viterbi decoding for WAV file.

    Parameters
    ----------
    wav_path : pathlib.Path
        Path to WAV file to be decoded.

    config : HViteConfig
        Config file defining paths to files defining network.

    working_dir : pathlib.Path
        Path to working directory for intermediate and output files.

    Returns
    -------
    lab_path : pathlib.Path
        Path to output label file.
    """
    # Check that HVite exists.
    # TODO: Update link when docs are online.
    if not which('HVite'):
        raise FileNotFoundError(
            f'HVite is not installed. Please install HTK and try again: '
            f'[INSERT LINK TO INSTRUCTIONS HERE]') from None

    # Run HVite.
    wav_path = Path(wav_path)
    cmd = ['HVite',
           '-T', '0',
           '-w', str(config.slf_path),
           '-l', str(working_dir),
           '-H', str(config.macros_path),
           '-H', str(config.hmmdefs_path),
           '-C', str(config.config_path),
           '-p', '-0.3',  # TODO: Pass as param.
           '-s', '5.0',
           '-y', 'lab',
           str(config.dict_path),
           str(config.monophones_path),
           wav_path,
          ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except CalledProcessError as e:
        if e.returncode == -11:
            raise HTKSegfault('HVite call caused segfault.') from None
        elif e.stderr:
            raise HTKError(f'HVite failed with following error: \n{e.stderr}') from None
        else:
            raise e

    return wav_path.with_suffix('.lab')


def write_hmmdefs(old_hmmdefs_path, new_hmmdefs_path, speech_scale_factor=1,
                  speech_phones=None):
    """Modify an HTK hmmdefs file in which speech model acoustic likelihoods
    are scaled by ``speech_scale_factor``.

    Parameters
    ----------
    old_hmmdefs_path : pathlib.Path
        Path to original HTK `hmmdefs` file.

    new_hmmsdefs_path : str
        Path for modified HTK `hmmdefs` file. If file already exists, it
        will be overwritten.

    speech_scale_factor : float, optional
        Factor by which speech model acoustic likelihoods are scaled prior to
        beam search.
        (Default: 1)

    speech_phones : Iterable[str], optional
        Names of speech phones. Only relevant when `speech_scale_factor != 1`.
        If None, `speech_scale_factor` has no effect.
        (Default: None)
    """
    old_hmmdefs_path = Path(old_hmmdefs_path)
    new_hmmdefs_path = Path(new_hmmdefs_path)
    if speech_phones is None:
        speech_phones = set()
    speech_phones = set(speech_phones)
    with open(old_hmmdefs_path, 'r', encoding='utf-8') as f:
        with open(new_hmmdefs_path, 'w', encoding='utf-8') as g:
            # Header.
            for _ in range(3):
                g.write(f.readline())

            # Model definitions.
            curr_phone = None
            for line in f:
                if line.startswith('~h'):
                    curr_phone = line[3:].strip('"\n')
                if (line.startswith('<GCONST>') and
                    speech_scale_factor != 1 and
                    curr_phone in speech_phones):
                    # Modify GCONST only for mixtures of speech models.
                    gconst = float(line[9:-1])
                    gconst += log(speech_scale_factor)
                    line = f'<GCONST> {gconst:.6e}\n'
                g.write(line)
