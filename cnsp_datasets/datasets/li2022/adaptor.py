from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import numpy as np
import scipy.io as sio
import soundfile as sf
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import mark_bads, read_wav
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

log = logging.getLogger(__name__)

EEG_FS = 1000.0
EEG = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fz', 'Cz',
       'Pz', 'Oz', 'FC1', 'FC2', 'CP1', 'CP2', 'FC5', 'FC6', 'CP5', 'CP6', 'TP9', 'TP10', 'POz', 'F1', 'F2', 'C1',
       'C2', 'P1', 'P2', 'AF3', 'AF4', 'FC3', 'FC4', 'CP3', 'CP4', 'PO3', 'PO4', 'F5', 'F6', 'C5', 'C6', 'P5', 'P6',
       'AF7', 'AF8', 'FT7', 'FT8', 'TP7', 'TP8', 'PO7', 'PO8', 'FT9', 'FT10', 'Fpz', 'CPz', 'FCz']
# Presentation order of S9-S17 (wav numbers; the authors' db/SCUT.py scut_suf_order). S1-S8 heard Trail1..32 in order.
ORDER_B = [24, 8, 32, 31, 7, 15, 29, 6, 12, 26, 9, 1, 5, 28, 20, 11, 30, 21, 2, 4, 10, 13, 17, 25, 14, 22, 23, 19, 16,
           27, 18, 3]
# Attended side (0 = left = clean channel 0) and talker (0 = male) per wav for S1-S8 (authors' scut_label);
# S9-S17 attended the other talker of the same wav (authors' _reverse_label; checked with the DNN, notes.md 6).
ATT_SIDE = [0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0]
ATT_TALKER = [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1]
SIDES = ("left", "right")
BADS = {"S4": ["P4", "PO4"]}  # low neighbour correlation and 3-4x the median SD (notes.md 5)
# The sound starts 0.216 s after the S marker (brain-based, notes.md section 6; applied by default, rule in
# CLAUDE.md): accou2023 match-mismatch DNN offset of the attended talker pooled over 17 subjects (95% CI
# 0.210-0.219 s; the ignored talker gives 0.213 s); per-block outliers are side lobes (TRFs agree within 23 ms).
ONSET_CORRECTION_S = 0.216
DNN_METHOD = ("brain-based, constant: accou2023 match-mismatch DNN offset of the attended talker, pooled over 17 "
              "subjects and 544 trials (notes.md section 6; circular: estimated from this EEG)")
NOTES = ("Software markers (trial<k>D/S/E, k = wav number) on BrainVision 20 ms blocks; (E - S) exceeds the wav "
         "duration by -20..+60 ms (mean +17, SD 19 ms): jitter_ms = 19 / sqrt(2) per marker. Onset = S + "
         "onset_correction_s. No drift measurable (DNN early vs late windows: -54 ppm, within noise); not "
         "corrected. The EEG ends with the sound (or the recording). Shipped re-referenced to the average of the 64 "
         "EEG channels (they sum to zero); FCz is a channel. Clean channel 0 is the left talker (+-90 deg HRTF).")


class Li2022Adaptor(BaseAdaptor):
    """
    Li et al. 2022 ESAA (Zenodo 7795585): 17 listeners (S1-S17 as shipped), 32 trials of 55-93 s, two Mandarin
    stories (male and female talker) HRTF-filtered to +-90 deg over insert phones; attend one. BrainAmp 64 EEG + ECG
    at 1000 Hz (the paper's 8192 Hz is wrong), one MATLAB file per subject (two for S4, S9, S12, S13, S14).

    Trial = presentation position; the stimulus is the marker's wav number. Condition `competing-f{L,R}-hrtf` by
    the attended side. Stimuli: the attended and the ignored clean talker (`Trail<k>_left` / `_right`, mono) and the
    as-played binaural mix (`Trail<k>_hrtf`, stereo, not attended). onset="dnn" (default) starts the EEG 0.216 s after
    the S marker, onset="marker" at the marker (notes.md section 6).
    """

    def __init__(self, download_dir: str, onset: str = "dnn"):
        super().__init__(download_dir)
        self.choice("onset", onset, ("dnn", "marker"))
        self.method = "dnn" if onset == "dnn" else "sw_trigger"
        self.onset = (dict(onset_correction_s=ONSET_CORRECTION_S, onset_correction_method=DNN_METHOD)
                      if onset == "dnn" else dict(onset_correction_s=0.0, onset_correction_method="none (S marker)"))
        self.mats, self.clean, self.hrtf = {}, {}, {}
        for dirpath, dirs, files in os.walk(download_dir):
            dirs.sort()  # deterministic walk; S<k>_1.mat before S<k>_2.mat
            # hrtf.zip unpacks to the download root (repo downloader) or to hrtf/ (per-zip extraction)
            wavs = self.clean if os.path.basename(dirpath) == "clean" else self.hrtf
            for f in sorted(files):
                if m := re.fullmatch(r"S(\d+)(?:_\d)?\.mat", f):
                    self.mats.setdefault(int(m[1]), []).append(os.path.join(dirpath, f))
                elif m := re.fullmatch(r"Trail(\d+)\.wav", f):
                    if int(m[1]) in wavs:
                        raise ValueError(f"two copies of {f}: {wavs[int(m[1])]}, {os.path.join(dirpath, f)}")
                    wavs[int(m[1])] = os.path.join(dirpath, f)
        if len(self.clean) != 32 or len(self.hrtf) != 32 or sorted(self.mats) != list(range(1, 18)):
            raise FileNotFoundError(f"expected S1-S17 *.mat and 32 clean + 32 HRTF Trail*.wav under {download_dir!r}")
        self.duration = {k: sf.info(p).duration for k, p in self.hrtf.items()}

    def parse(self) -> Iterable[TrialRecord]:
        for subject in sorted(self.mats):
            markers = {}  # wav -> (file, 0-based S sample, samples in file)
            for path in self.mats[subject]:
                n = dict((name, shape) for name, shape, _ in sio.whosmat(path))["t"][0]
                for e in sio.loadmat(path, variable_names=["Markers"])["Markers"][0]:
                    desc = str(np.ravel(e["Description"])[0]) if np.size(e["Description"]) else ""
                    if mk := re.fullmatch(r"trail(\d+)S", desc):
                        if int(mk[1]) in markers:  # not seen in the release; the later file's marker is used
                            log.warning("S%d: trail%sS marker in %s and %s", subject, mk[1], markers[int(mk[1])][0],
                                        path)
                        markers[int(mk[1])] = (path, int(np.ravel(e["Position"])[0]) - 1, n)  # 1-based
            if len(markers) != 32:
                raise ValueError(f"S{subject}: {len(markers)} trial start markers, expected 32")
            group_b = subject > 8
            for pos, wav in enumerate(ORDER_B if group_b else range(1, 33), 1):
                path, s_marker, n_file = markers[wav]
                side, talker = ATT_SIDE[wav - 1] ^ group_b, ATT_TALKER[wav - 1] ^ group_b
                onset = s_marker + round(self.onset["onset_correction_s"] * EEG_FS)
                stop = min(onset + round(self.duration[wav] * EEG_FS), n_file)
                description = self._description(subject, wav, side, talker, s_marker, onset, stop)
                yield TrialRecord(
                    subject=subject, session=1, trial=pos, condition=f"competing-f{'LR'[side]}-hrtf", ns_type="eeg",
                    stimulus=[StimulusRecord("audio", f"Trail{wav}_{SIDES[side]}",
                                             _audio_loader(self.clean[wav], side), is_attended=True),
                              StimulusRecord("audio", f"Trail{wav}_{SIDES[1 - side]}",
                                             _audio_loader(self.clean[wav], 1 - side)),
                              StimulusRecord("audio", f"Trail{wav}_hrtf", _audio_loader(self.hrtf[wav], None))],
                    neural_data_fn=_eeg_loader(path, onset, stop, BADS.get(f"S{subject}", []), description),
                )

    def _description(self, subject: int, wav: int, side: int, talker: int, s_marker: int, onset: int,
                     stop: int) -> str:
        recorded = (stop - onset) / EEG_FS
        return provenance(
            self.method, "software (BrainVision markers on 20 ms blocks, inferred; not documented)", NOTES,
            drift_ppm=None, jitter_ms=13.0, validation_tier="low", participant=f"S{subject}", wav=f"Trail{wav}",
            attended_side=SIDES[side], attended_talker=("male", "female")[talker],
            s_marker_sample=s_marker, onset_sample=onset, **self.onset,
            eeg_truncated_s=max(0.0, round(self.duration[wav] - recorded, 3)),
            units_as_shipped="microvolts (MATLAB doubles)",
            reference="common average of the 64 EEG channels (as shipped; the online reference is not documented)",
            external_sensors={},
        )


@lru_cache(maxsize=1)
def _read_mat(path: str) -> dict:
    """Whole subject file, cached: its trials are read consecutively."""
    return sio.loadmat(path, variable_names=EEG + ["ECG"])


def _eeg_loader(path: str, onset: int, stop: int, bads: list, description: str) -> Callable[[], BaseRaw]:
    """Samples [onset, stop) of the 64 EEG + ECG channels, uV -> V, standard_1020 positions."""
    def _loader() -> BaseRaw:
        m = _read_mat(path)
        x = 1e-6 * np.array([m[c][onset:stop, 0] for c in EEG + ["ECG"]])  # microvolts as shipped
        raw = RawArray(x, create_info(EEG + ["ECG"], EEG_FS, ["eeg"] * 64 + ["ecg"]), verbose="ERROR")
        raw.set_montage(make_standard_montage("standard_1020"), verbose="ERROR")
        mark_bads(raw, bads)
        raw.info["description"] = description
        return raw
    return _loader


def _audio_loader(path: str, channel: int | None) -> Callable[[], dict]:
    """
    Clean talker `channel` of the stereo clean wav (0 = left talker, 1 = right talker; one mono channel) or both
    HRTF ears (channel None); 44.1 kHz as shipped, float32.
    """
    def _loader() -> dict:
        x, fs = read_wav(path, channel=channel)
        return {"fs": fs, "data": x}
    return _loader


ADAPTOR = Li2022Adaptor
