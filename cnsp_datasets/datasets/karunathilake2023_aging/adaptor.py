from __future__ import annotations

import glob
import os
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from mne.io.constants import FIFF
from scipy.io import loadmat, wavfile, whosmat

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 250
AUDIO_FS = 22050
N_ARRAY = 15000     # 60 s arrays as shipped
DELAY = 375         # 1.5 s group delay of the authors' causal FIR (notes.md section 6)
N_COMP = 6
BABBLE_GAIN = 0.714  # babble track gain in the babble mixture (notes.md section 3)
FOREGROUND = "babb_F08_foreground_derived"
JUNK_SOLO9 = {509, 629, 654, 660, 665, 666}  # junk 9th dss_solo row (notes.md section 3)
AUDITORY_COMPONENT = {594: 2}  # paper / TRF.m; component 1 for everyone else
SOLO = ["M08", "M02", "F10", "F04", "F03", "F07", "M01", "M05"]  # dss_solo rows 1-8
# two-talker mixtures, three dss_mix rows each: (condition, played wav, attended, unattended, attended talker)
MIX = [("snr0dB", "pass_mix_M0_M08_F10", "pass_single_M08", "pass_single_F10", "M"),
       ("snr-6dB", "pass_mix_M6_M02_F04", "pass_single_M02", "pass_single_F04", "M"),
       ("snr0dB", "pass_mix_F0_F03_M01", "pass_single_F03", "pass_single_M01", "F"),
       ("snr-6dB", "pass_mix_F6_F07_M05", "pass_single_F07", "pass_single_M05", "F")]
# TRIALS: (array, 0-based row, condition, played wav, attended, unattended, attended talker);
# rows as stored, mapping verified in notes.md section 3
TRIALS = ([("dss_solo", i, "quiet", f"pass_single_{t}", f"pass_single_{t}", None, t[0]) for i, t in enumerate(SOLO)]
          + [("dss_mix", 3 * b + r, *MIX[b]) for b in range(4) for r in range(3)]
          + [("dss_babble", r, "babble", "babb_mix_F08_BF08", FOREGROUND, "babb_singleQ_BF08", "F")
             for r in range(3)])
TALKER = {"F": "female", "M": "male"}
SNR_DB = {"quiet": None, "snr0dB": 0.0, "snr-6dB": -6.0, "babble": 0.0}
NOTES = ("Shared data are the first 6 DSS components (dss1-dss6, ranked by trial-to-trial reproducibility) of "
         "TSPCA/SNS-cleaned KIT 157-channel MEG, causally FIR-filtered 1-10 Hz (fir1 order 6000 at 2 kHz) and "
         "downsampled to 250 Hz by the authors; no sensor data. Channels are `misc` with unit FIFF_UNIT_NONE "
         "(arbitrary units, not physical); components as stored (no sign alignment, no reordering). The authors "
         "epoched each trial to 60 s from stimulus onset before the causal filter; the first 375 samples (1.5 s "
         "group delay) are dropped so t = 0 is stimulus onset, leaving 58.5 s (the stimulus is longer: cut at use). "
         "The first ~1.5 s still carry the filter transient. Onset uncertainty: decimation phase and any "
         "trigger/tube delay unknown. Presentation order unknown: trial numbers follow the shipped array order.")
DERIVED = f"{FOREGROUND}: babb_mix_F08_BF08 - {BABBLE_GAIN} * babb_singleQ_BF08"
BABBLE_NOTE = (f" Attended stimulus `{FOREGROUND}` is derived: babb_mix_F08_BF08 - {BABBLE_GAIN} * "
               "babb_singleQ_BF08 (the played foreground; not sample-identical to pass_single_F08).")


class Karunathilake2023AgingAdaptor:
    """
    Karunathilake et al. 2023 (DRUM 10.13016/4goq-vs0z): 18 younger + 16 older listeners, Sleepy Hollow passages
    in quiet, with a competing talker at 0 / -6 dB SNR (attended talker 6 dB softer; the paper says "6 dB") and in
    three-talker babble. Only 6 DSS components per subject are shared (1-10 Hz, 250 Hz kept): `misc` channels
    dss1-dss6, arbitrary units. Subject = R-number - 2000 (R2509 -> 509). 23 trials per subject: 1-8 quiet, 9-20
    two-talker (`snr0dB`, `snr-6dB`, three repetitions per mixture), 21-23 `babble`. Each trial starts at
    stimulus onset (1.5 s filter delay removed) and lasts 58.5 s. Stimuli (22.05 kHz wavs as shipped): quiet =
    the single talker (attended); two-talker = attended + mixture as played + unattended single talker; babble =
    derived foreground (attended, `babb_F08_foreground_derived`) + mixture as played + babble track. No drift
    correction (not estimable). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, "Data")

    def parse(self) -> Iterable[TrialRecord]:
        for group in ("Younger", "Older"):
            for mat in sorted(glob.glob(os.path.join(self.root, "MEG", group, "R*_todss_250hz.mat"))):
                pid = os.path.basename(mat).split("_")[0]
                subject = int(pid[1:]) - 2000  # R2509 -> 509: the sink allows 3-digit subject numbers
                shapes = {n: s for n, s, _ in whosmat(mat)}
                n_solo = 9 if subject in JUNK_SOLO9 else 8
                expected = {"dss_solo": (n_solo, N_ARRAY, N_COMP), "dss_mix": (12, N_ARRAY, N_COMP),
                            "dss_babble": (3, N_ARRAY, N_COMP)}
                if any(shapes.get(k) != v for k, v in expected.items()):
                    raise ValueError(f"{mat}: unexpected array shapes {shapes}")
                for trial, (array, row, cond, played, attended, unattended, talker) in enumerate(TRIALS, 1):
                    babble = cond == "babble"
                    extra = {"derived_stimulus": DERIVED} if babble else {}
                    notes = NOTES + (BABBLE_NOTE if babble else "")
                    description = provenance(
                        "onset_only", "unknown (not documented; epochs cut at stimulus onset by the authors)", notes,
                        participant=pid, age_group=group.lower(), array=array, array_row_1based=row + 1, played=played,
                        attended=attended, unattended=unattended, snr_db=SNR_DB[cond],
                        attended_talker=TALKER[talker], **extra,
                        auditory_component=f"dss{AUDITORY_COMPONENT.get(subject, 1)}",
                        onset_shift_samples=DELAY, presentation_order="unknown",
                        units_as_shipped="arbitrary (DSS component projections)",
                        reference="not applicable (DSS components of KIT axial gradiometers)",
                        preprocessing="TSPCA, SNS, causal FIR 1-10 Hz, DSS, 250 Hz (authors)")
                    yield TrialRecord(
                        subject=subject, session=1, trial=trial, condition=cond, ns_type="meg",
                        stimulus=self._stimuli(played, attended, unattended),
                        neural_data_fn=_meg_loader(mat, array, row, description))

    def _stimuli(self, played: str, attended: str, unattended: str | None) -> list[StimulusRecord]:
        """Quiet: the single talker; otherwise attended, played mixture, unattended (in that order)."""
        if played == attended:
            return [StimulusRecord("audio", played, self._audio(played), is_attended=True)]
        target = self._foreground if attended == FOREGROUND else self._audio(attended)
        return [StimulusRecord("audio", attended, target, is_attended=True),
                StimulusRecord("audio", played, self._audio(played), is_attended=False),
                StimulusRecord("audio", unattended, self._audio(unattended), is_attended=False)]

    def _audio(self, name: str) -> Callable[[], dict]:
        return lambda: {"fs": AUDIO_FS, "data": _read_wav(self._wav(name)).astype(np.float32)[None, :]}

    def _foreground(self) -> dict:
        """Derived babble foreground: mixture minus BABBLE_GAIN times the babble track (notes.md section 3)."""
        mix, babble = _read_wav(self._wav("babb_mix_F08_BF08")), _read_wav(self._wav("babb_singleQ_BF08"))
        return {"fs": AUDIO_FS, "data": (mix - BABBLE_GAIN * babble).astype(np.float32)[None, :]}

    def _wav(self, name: str) -> str:
        return os.path.join(self.root, "stimuli", f"{name}.wav")


def _read_wav(path: str) -> np.ndarray:
    fs, x = wavfile.read(path)
    if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
        raise ValueError(f"{path}: expected {AUDIO_FS} Hz mono int16")
    return x / 32768.0


@lru_cache(maxsize=1)
def _read(mat: str) -> dict:
    """All three arrays of one subject (~17 MB)."""
    return loadmat(mat, variable_names=["dss_solo", "dss_mix", "dss_babble"])


def _meg_loader(mat: str, array: str, row: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    def _loader() -> mne.io.BaseRaw:
        x = _read(mat)[array]
        info = mne.create_info([f"dss{i + 1}" for i in range(N_COMP)], FS, "misc")
        for ch in info["chs"]:
            ch["unit"] = FIFF.FIFF_UNIT_NONE
        raw = mne.io.RawArray(np.ascontiguousarray(x[row, DELAY:].T), info, verbose="ERROR")
        raw.info["description"] = description
        return raw

    return _loader


ADAPTOR = Karunathilake2023AgingAdaptor
