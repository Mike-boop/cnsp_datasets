from __future__ import annotations

import glob
import os
from typing import Iterable

import h5py
import numpy as np

from cnsp_datasets.datasets.maddox_base.common import bits_to_ints, load_trial, read_recording, recording_sfreq
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import read_wav
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_AUDIO = 48000
FS_TDT = 390625 / 16          # 24414.0625 Hz, exp2 wavs
DUR_EXP12 = 64.0
DUR_EXP3 = 8214463 / FS_AUDIO  # padded stimuli, 171.13 s
END_EXP1 = 63.98               # S 2 offset
END_EXP3 = 171.11464583333333  # S 2 offset (authors' tab file)
DRIFT_EXP1_06 = 24.8e-6        # sub-diotic06 has no S 2: median of sub-diotic01..16
DRIFT_EXP2 = -5e-6             # no S 2 in exp2: from the ER-2 artefact (notes section 8)
EXP3_REVERSED = {17}           # polarity of repetitions 1/3 vs 2/4 reversed (notes section 10)
TALKERS = {"alc": "alchemyst", "wri": "wrinkle"}
MONTAGES = ("subcortex", "cortex")


class Stoll2025Adaptor(BaseAdaptor):
    """
    Stoll et al. 2025 (OpenNeuro ds006434): attention to one of two audiobooks (Wrinkle in Time, female; The
    Alchemyst, male) and passive listening; the subcortical montage by default (montage="cortex": the 32-channel
    cortical files of exp1 and exp2, see datasets/stoll2025_cortex). Subjects: exp1 101-129, exp2 202-225, exp3
    317-331 (label number + 100 x experiment). See notes.md for every choice below.

    exp1 (diotic): 120 x 64 s, chapter pair summed, attend one talker; trial ID after S 1 = [attended (1 bit,
      0 female), chapter (6)]. Stimuli `alchemyst_chNN`, `wrinkle_chNN` (stored = played; flip_signs is not needed):
      `audio` 48 kHz, `pulses` (glottal pulse train), optional `anm` (two polarities).
    exp2 (dichotic, TDT): 60 x 64 s; ID before S 1 = [chapter (6), attended story (1), attended side (1)]; wav
      channel 0 = Wrinkle, 1 = Alchemyst (`<talker>_dichotic_chNN`, 24414.0625 Hz). Side 0/1 -> left/right is
      undocumented: conditions say `side0`/`side1` (the attended talker's side). Trials restarted before 64 s
      (sub-dichotic12) or cut by the end of the recording (sub-dichotic02) are skipped.
    exp3 (passive, 25 kHz): 8 story/distractor pairs x 4 consecutive repetitions, polarity alternating across
      repetitions (stored waveform in repetitions 1 and 3; reversed in sub-passive17; sub-passive20 unverified);
      `exp3_<fM|fW>_<story|distractor>K[_inv]`, 48 kHz, 171.13 s padded.
    Markers include the ER-2 tube delay (ER-2 artefact at -0.8 ms). Drift: exp1/exp3 from S 2 per recording
    (sub-diotic06: 24.8 ppm), exp2 -5 ppm; applied in the resample. sfreq=1000 by default (never upsampled).
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True,
                 montage: str = "subcortex", save_anm: bool = False):
        super().__init__(download_dir)
        self.sfreq = sfreq
        self.drift_correction = drift_correction
        self.montage = self.choice("montage", montage, MONTAGES)
        self.save_anm = save_anm
        self._stim1 = os.path.join(download_dir, "stimuli", "exp1Diotic", "stim+pulses+silences.hdf5")

    def parse(self) -> Iterable[TrialRecord]:
        yield from self._exp1()
        yield from self._exp2()
        if self.montage == "subcortex":
            yield from self._exp3()

    # --- helpers -------------------------------------------------------------------------------------------
    def _files(self, prefix: str, task: str):
        return sorted(glob.glob(os.path.join(self.download_dir, f"sub-{prefix}*", "eeg", f"*_task-{task}_eeg.vhdr")))

    def _neural(self, sub_vhdr: str, onset_s: float, duration: float, drift: float):
        """EEG loader: the montage's file, onset in seconds from the subcortical markers (same recording)."""
        vhdr = sub_vhdr.replace("Subcortex", "Cortex") if self.montage == "cortex" else sub_vhdr
        sfreq, drift = self.sfreq, drift if self.drift_correction else 0.0

        def _loader():
            return load_trial(vhdr, onset_s * recording_sfreq(vhdr), duration, sfreq, drift)

        return _loader

    # --- exp1 ----------------------------------------------------------------------------------------------
    def _exp1(self):
        for vhdr in self._files("diotic", "exp1DioticSubcortex"):
            label = int(os.path.basename(vhdr)[10:12])
            rec = read_recording(vhdr)
            drift = rec.drift(END_EXP1 * rec.sfreq)
            drift = drift if np.isfinite(drift) else DRIFT_EXP1_06
            for i, t in enumerate(rec.trials, start=1):
                if not rec.usable(t, int(DUR_EXP12 * rec.sfreq)):
                    continue
                attend, ch = bits_to_ints(t.bits, (1, 6))
                yield TrialRecord(
                    subject=100 + label, session=1, trial=i,
                    condition=f"diotic-attend-{('female', 'male')[attend]}", ns_type="eeg",
                    stimulus=[s for k in ("wri", "alc") for s in self._exp1_stimuli(k, ch, k == ("wri", "alc")[attend])],
                    neural_data_fn=self._neural(vhdr, t.start / rec.sfreq, DUR_EXP12, drift))

    def _exp1_stimuli(self, key: str, ch: int, attended: bool) -> list:
        name = f"{TALKERS[key]}_ch{ch:02d}"
        path = self._stim1
        stims = [StimulusRecord("audio", name, _h5_loader(path, f"expyfun/key_{key}_aud_all", (ch, 0)),
                                is_attended=attended, feature_name="audio"),
                 StimulusRecord("audio", name, _pulse_loader(path, f"expyfun/key_{key}_pulse_inds_all/idx_{ch}/idx_0",
                                                             int(DUR_EXP12 * FS_AUDIO)),
                                is_attended=attended, feature_name="pulses")]
        if self.save_anm:
            anm = os.path.join(self.download_dir, "stimuli", "exp1Diotic", "anm_regressors.hdf5")
            stims.append(StimulusRecord("audio", name, _h5_loader(anm, f"h5io/key_{key}_anm", (slice(None), ch)),
                                        is_attended=attended, feature_name="anm"))
        return stims

    # --- exp2 ----------------------------------------------------------------------------------------------
    def _exp2(self):
        for vhdr in self._files("dichotic", "exp2DichoticSubcortex"):
            label = int(os.path.basename(vhdr)[12:14])
            rec = read_recording(vhdr, ids_before_start=True)
            n = int(DUR_EXP12 * rec.sfreq)
            starts = [t.start for t in rec.trials] + [None]
            for i, t in enumerate(rec.trials, start=1):
                restarted = starts[i] is not None and starts[i] - t.start < n
                if restarted or not rec.usable(t, n):
                    continue
                ch, story, side = bits_to_ints(t.bits, (6, 1, 1))
                wav = os.path.join(self.download_dir, "stimuli", "exp2Dichotic", f"wrinkle_alchemyst{ch:03d}.wav")
                stims = [StimulusRecord("audio", f"{TALKERS[k]}_dichotic_ch{ch:02d}", _wav_loader(wav, col),
                                        is_attended=(col == story), feature_name="audio")
                         for col, k in enumerate(("wri", "alc"))]
                yield TrialRecord(
                    subject=200 + label, session=1, trial=i,
                    condition=f"dichotic-attend-{('female', 'male')[story]}-side{side}", ns_type="eeg",
                    stimulus=stims, neural_data_fn=self._neural(vhdr, t.start / rec.sfreq, DUR_EXP12, DRIFT_EXP2))

    # --- exp3 ----------------------------------------------------------------------------------------------
    def _exp3(self):
        path = os.path.join(self.download_dir, "stimuli", "exp3Passive", "stimdict_padded_48k")
        for vhdr in self._files("passive", "exp3Passive"):
            label = int(os.path.basename(vhdr)[11:13])
            rec = read_recording(vhdr)
            drift = rec.drift(END_EXP3 * rec.sfreq)
            previous, rep = None, 0
            for i, t in enumerate(rec.trials, start=1):
                order, focus = bits_to_ints(t.bits, (3, 1))
                rep = rep + 1 if (order, focus) == previous else 0
                previous = (order, focus)
                if not rec.usable(t, int(DUR_EXP3 * rec.sfreq)):
                    continue
                invert = (rep % 2 == 1) != (label in EXP3_REVERSED)
                fo, k = ("fM", "fW")[focus], order - 1
                stims = [StimulusRecord("audio", f"exp3_{fo}_{part}{k}" + ("_inv" if invert else ""),
                                        _h5_loader(path, f"expyfun/key_stim/key_{fo}/key_{part}", (k,), invert),
                                        feature_name="audio")
                         for part in ("story", "distractor")]
                yield TrialRecord(
                    subject=300 + label, session=1, trial=i, condition=f"passive-{fo}", ns_type="eeg",
                    stimulus=stims, neural_data_fn=self._neural(vhdr, t.start / rec.sfreq, DUR_EXP3, drift))


def _h5_loader(path: str, key: str, index: tuple, invert: bool = False):
    def _loader() -> dict:
        with h5py.File(path, "r") as f:
            data = np.atleast_2d(f[key][index]).astype(np.float32)
        return {"fs": FS_AUDIO, "data": -data if invert else data}

    return _loader


def _pulse_loader(path: str, key: str, n_times: int):
    def _loader() -> dict:
        with h5py.File(path, "r") as f:
            idx = f[key][()]
        train = np.zeros((1, n_times), np.uint8)
        train[0, idx[idx < n_times].astype(int)] = 1
        return {"fs": FS_AUDIO, "data": train}

    return _loader


def _wav_loader(path: str, column: int):
    """One channel of a dichotic wav as float32 (1, n); fs = FS_TDT (the header says 24414 Hz)."""
    def _loader() -> dict:
        data, _ = read_wav(path, channel=column)
        return {"fs": FS_TDT, "data": data}

    return _loader


ADAPTOR = Stoll2025Adaptor
