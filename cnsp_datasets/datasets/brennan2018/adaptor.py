from __future__ import annotations

import glob
import os
from typing import Any, Callable, Dict, Iterable

import mne
import numpy as np
import pandas as pd
from mne.channels import make_standard_montage
from mne.io import BaseRaw
from scipy.fft import irfft, next_fast_len, rfft
from scipy.io import wavfile
from scipy.signal import butter, resample_poly, sosfiltfilt

from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 500
STIMTRACK = ("Aux5", "AUD")
SEARCH_S = 3.0   # stimtrack search window around the software onset
MIN_QUALITY = 10  # stimtrack peak height in robust SDs of the cross-correlation; below it, use the software onset


def _band(x: np.ndarray) -> np.ndarray:
    # the actiCHamp low-passes at 200 Hz; the stimtrack also carries slow drifts
    return sosfiltfilt(butter(4, [1.0, 200.0], "bandpass", fs=FS, output="sos"), x)


def _xcorr_peak(track: np.ndarray, feat: np.ndarray, centre: int | None) -> tuple[float, float]:
    """Sub-sample position of feat in track (searched around centre, or everywhere) and the peak quality."""
    lo = 0 if centre is None else max(0, centre - int(SEARCH_S * FS))
    seg = track if centre is None else track[lo:lo + len(feat) + int(2 * SEARCH_S * FS)]
    n = next_fast_len(len(seg) + len(feat))
    g = irfft(rfft(seg, n) * np.conj(rfft(feat, n)), n)[:len(seg) - len(feat) + 1]
    energy = np.concatenate([[0.0], np.cumsum(seg ** 2)])  # sliding energy of seg under feat, in linear time
    g /= np.sqrt(np.maximum(energy[len(feat):] - energy[:-len(feat)], 0)) + 1e-12
    i = int(np.argmax(g))
    frac = 0.0
    if 0 < i < len(g) - 1:
        a, b, c = g[i - 1:i + 2]
        frac = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c < 0 else 0.0
    rest = np.delete(g, slice(max(0, i - 50), i + 50))
    quality = (g[i] - np.median(rest)) / (1.4826 * np.median(np.abs(rest - np.median(rest))) + 1e-12)
    return lo + i + frac, float(quality)


class Brennan2018Adaptor:
    """
    Brennan & Hale (2019) "Alice" EEG, from the BIDS mirror on NEMAR (nm000180, 45 of the 49 participants;
    sub-XXX is the original SXX).

    Layout: sub-*/eeg/*_eeg.vhdr (continuous BrainVision, 500 Hz, volts once loaded), *_events.tsv (word onsets,
    missing for subjects excluded in the original study), stimuli/DownTheRabbitHoleFinal_SoundFile{1..12}.wav,
    sourcedata/AliceChapterOne-EEG.csv (word timing within each segment).

    One trial per subject x audio segment (1..12). The re-hosted recordings carry no segment triggers, so onsets come
    from, in order of preference:
      1) "stimtrack": cross-correlating the stimtrack channel (Aux5/AUD, a copy of the audio as presented, closest to
         its full-wave rectified waveform) with the segment audio, when the peak is clear (quality > MIN_QUALITY);
      2) "software": the first word onset in events.tsv minus that word's onset in the segment. These derive from the
         E-Prime (software) triggers plus the authors' delay correction; against the stimtrack they scatter by a few
         ms per segment.
    Segments with neither are skipped. The method is stored in raw.info["description"].

    Channels: 60 scalp EEG ('eeg', easycap-M10 positions), VEOG ('eog'), the stimtrack ('misc').
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self.words = pd.read_csv(os.path.join(download_dir, "sourcedata", "AliceChapterOne-EEG.csv"))
        self.durations, self.templates = {}, {}
        for seg in range(1, 13):
            fs, a = wavfile.read(self._wav_path(seg))
            self.durations[seg] = len(a) / fs
            self.templates[seg] = _band(resample_poly(np.abs(a.astype(float)), FS, fs))

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for vhdr in sorted(glob.glob(os.path.join(self.root, "sub-*", "eeg", "*_eeg.vhdr"))):
            subject = int(os.path.basename(vhdr).split("_")[0].replace("sub-", ""))
            onsets = self._segment_onsets(vhdr)
            for seg, (onset, method) in onsets.items():
                name = f"DownTheRabbitHoleFinal_SoundFile{seg}"
                stimuli = [
                    StimulusRecord("audio", name, self._make_audio_loader(seg), True, feature_name="audio"),
                    StimulusRecord("audio", name, self._make_textgrid_loader(seg), True, feature_name="textgrid"),
                ]
                yield TrialRecord(
                    subject=subject,
                    session=1,
                    trial=seg,
                    condition="natural",
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=self._make_eeg_loader(vhdr, onset, self.durations[seg], method),
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------ Alignment ------------------------

    def _segment_onsets(self, vhdr: str) -> Dict[int, tuple[float, str]]:
        """Onset (s) and method of each segment that can be placed."""
        raw = mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
        track = raw.get_data(picks=[c for c in raw.ch_names if c in STIMTRACK])[0]
        usable = track.std() > 0  # flat in sub-005 and sub-038
        if usable:
            pad = max(len(t) for t in self.templates.values()) + int(2 * SEARCH_S * FS)
            track = np.pad(_band(track), (0, pad))  # recordings may end during the last segment
        software = self._software_onsets(vhdr.replace("_eeg.vhdr", "_events.tsv"))

        onsets = {}
        for seg in range(1, 13):
            sw = software.get(seg)
            if usable:
                pos, quality = _xcorr_peak(track, self.templates[seg], None if sw is None else round(sw * FS))
                if quality > MIN_QUALITY:
                    onsets[seg] = (pos / FS, f"stimtrack (xcorr quality {quality:.0f})")
                    continue
            if sw is not None:
                onsets[seg] = (sw, "software (events.tsv)")
        return onsets

    def _software_onsets(self, events_tsv: str) -> Dict[int, float]:
        """Segment onsets implied by the first word of each segment in events.tsv."""
        if not os.path.exists(events_tsv):
            return {}
        ev = pd.read_csv(events_tsv, sep="\t").sort_values("onset").groupby("segment").first()
        in_segment = self.words.set_index("Order").onset
        return {int(seg): row.onset - in_segment[row.word_index] for seg, row in ev.iterrows()}

    # ------------------------ Lazy loaders ------------------------

    def _make_eeg_loader(self, vhdr: str, onset_s: float, duration_s: float, method: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            raw = mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
            tmax = min(onset_s + duration_s, raw.times[-1])
            raw.crop(max(onset_s, 0.0), tmax, include_tmax=False).load_data(verbose="ERROR")
            types = {c: "misc" if c in STIMTRACK else "eog" if c == "VEOG" else "eeg" for c in raw.ch_names}
            raw.set_channel_types(types, verbose="ERROR")
            raw.set_montage(make_standard_montage("easycap-M10"), match_case=False, on_missing="ignore")
            raw.info["description"] = f"segment onset {onset_s:.4f} s in the continuous recording; alignment: {method}"
            return raw
        return _loader

    def _make_audio_loader(self, seg: int) -> Callable[[], Dict[str, Any]]:
        def _loader() -> Dict[str, Any]:
            fs, a = wavfile.read(self._wav_path(seg))
            return {"fs": int(fs), "data": (a.astype(np.float32) / 32768.0)[None, :]}
        return _loader

    def _make_textgrid_loader(self, seg: int) -> Callable[[], str]:
        w = self.words[self.words.Segment == seg]
        tier = {"item": w.Word.tolist(), "onset_s": w.onset.tolist(), "offset_s": w.offset.tolist()}
        return lambda: multi_tier_dict_to_textgrid({"words": tier})

    def _wav_path(self, seg: int) -> str:
        return os.path.join(self.root, "stimuli", f"DownTheRabbitHoleFinal_SoundFile{seg}.wav")


ADAPTOR = Brennan2018Adaptor
