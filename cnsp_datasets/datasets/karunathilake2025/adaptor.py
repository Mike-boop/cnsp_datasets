from __future__ import annotations

import glob
import os
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1000
AUDIO_FS = 22050
# Trigger code -> stimulus (exp.py ACOUSTICS, PHONEMES, LEXICAL, SEMANTIC); 177 is not used.
CODES = {164: "ASN_M01", 165: "ASN_M02", 166: "ASN_M03", 167: "ASN_M04", 168: "PH_M01", 169: "PH_M02",
         170: "PH_M03", 171: "PH_M04", 172: "ASM_M01", 173: "ASM_M02", 174: "ASM_M03", 175: "ASM_M04",
         176: "AS_M01", 178: "AS_M02", 179: "AS_M03", 180: "AS_M04"}
# Passage-type prefix -> condition (exp.py epoch names).
CONDITIONS = {"ASN": "noise", "PH": "nonwords", "ASM": "scrambled", "AS": "narrative"}
FLAT_RATIO = 20  # channel rms below median / 20 in 10 x 10 s windows -> bad (flat; notes.md section 5)
SATURATED_RATIO = 30  # ... or above 30 x median -> bad (R2682 MEG 086 jumps between the rails, 88 x median)
TRIGGER_TYPE = ("software (inferred: TTL codes from the stimulus PC, recorded on MISC 009 and STI 014; latency "
                "to sound onset and tube delay unknown, no audio channel)")
NOTES = ("Onset = trigger (one TTL code per passage onset, no offset codes), no shift and no drift correction (no "
         "audio channel and no offset triggers: drift not measurable; ~1-3 ms over a 62 s trial for typical "
         "clocks). Trial length = played wav. Units T. MEG 001-157 axial gradiometers (MNE type mag) + 3 reference "
         "magnetometers; MISC lines (TTL trigger lines, idle or noise-only ports) and STI 014 dropped. Flat and "
         "saturated channels in info['bads']. Each passage is played twice in a row; gTTS speech.")


class Karunathilake2025Adaptor:
    """
    Speech-modulated noise, nonwords, scrambled words and narrative passages (Karunathilake, Brodbeck, Bhattasali,
    Resnik & Simon 2025, J Neurosci; Dryad doi:10.5061/dryad.ht76hdrpf): KIT 157-channel MEG at 1 kHz, one
    recording per participant, 16 synthesised 1-min passages each played twice in a row (32 trials, presentation
    order). Subject = R-number mod 1000 (R-number in the sidecar). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(_find(self.root, "**/AS_M01.wav"))
        paths = sorted(glob.glob(os.path.join(self.root, "**", "R*", "R*_fif-raw.fif"), recursive=True))
        pids = [os.path.basename(p).split("_")[0] for p in paths]
        if len({int(pid[1:]) % 1000 for pid in pids}) != len(pids):
            raise ValueError("subject numbers (R-number mod 1000) are not unique")
        for path, pid in zip(paths, pids):
            raw = _read(path)
            events = mne.find_events(raw, stim_channel="STI 014", shortest_event=1, verbose="ERROR")
            events = events[np.isin(events[:, 2], list(CODES))]
            if (len(events) != 2 * len(CODES) or any((events[:, 2] == c).sum() != 2 for c in CODES)
                    or (events[0::2, 2] != events[1::2, 2]).any()):
                raise ValueError(f"{path}: expected each of {len(CODES)} codes twice in a row, got "
                                 f"{events[:, 2].tolist()}")
            count = dict.fromkeys(CODES, 0)
            for trial, (sample, code) in enumerate(events[:, [0, 2]].tolist(), 1):
                count[code] += 1
                name = CODES[code]
                prefix, passage = name.split("_M")
                onset = sample - raw.first_samp
                description = provenance(
                    "sw_trigger", TRIGGER_TYPE, NOTES, participant=pid, passage_type=CONDITIONS[prefix],
                    passage=int(passage), repetition=count[code], block=(trial - 1) // 8 + 1, trigger_code=code,
                    onset_s=onset / FS, stimulus_file=f"{name}.wav")
                wav = os.path.join(stim_dir, f"{name}.wav")
                yield TrialRecord(
                    subject=int(pid[1:]) % 1000, session=1, trial=trial, condition=CONDITIONS[prefix],
                    ns_type="meg",
                    stimulus=[StimulusRecord("audio", name, _audio(wav), is_attended=True)],
                    neural_data_fn=_meg_loader(path, onset, _n_samples(wav), description),
                )


def _find(root: str, pattern: str) -> str:
    hits = sorted(glob.glob(os.path.join(root, pattern), recursive=True))
    if len(hits) != 1:
        raise FileNotFoundError(f"{pattern}: {len(hits)} matches under {root}, expected 1")
    return hits[0]


def _audio(path: str) -> Callable[[], dict]:
    def _load():
        fs, x = wavfile.read(path)
        if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
            raise ValueError(f"{path}: expected {AUDIO_FS} Hz mono int16")
        return {"fs": AUDIO_FS, "data": (x / 32768.0).astype(np.float32)[None, :]}

    return _load


@lru_cache(maxsize=None)
def _n_samples(wav: str) -> int:
    """Played wav length in samples at FS."""
    fs, x = wavfile.read(wav, mmap=True)
    if fs != AUDIO_FS:
        raise ValueError(f"{wav}: expected {AUDIO_FS} Hz")
    return round(len(x) * FS / AUDIO_FS)


def _meg_loader(path: str, onset: int, n_out: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    def _loader():
        raw = _read(path)
        picks = mne.pick_types(raw.info, meg=True, ref_meg=True, exclude=[])
        out = crop_on_audio_clock(raw, onset, n_out, picks=picks)
        out.info["bads"] = list(_bad_channels(path))
        out.info["description"] = description
        return out

    return _loader


@lru_cache(maxsize=1)
def _read(path: str) -> mne.io.BaseRaw:
    """Continuous recording (opening R####_fif-raw.fif joins the -1 split where there is one)."""
    raw = mne.io.read_raw_fif(path, preload=False, verbose="ERROR")
    if raw.info["sfreq"] != FS:
        raise ValueError(f"{path}: sfreq {raw.info['sfreq']}, expected {FS}")
    return raw


@lru_cache(maxsize=4)
def _bad_channels(path: str) -> tuple:
    """Gradiometers whose median rms over 10 x 10 s windows is below the across-channel median / FLAT_RATIO or
    above the median x SATURATED_RATIO."""
    raw = _read(path)
    meg = mne.pick_types(raw.info, meg=True, ref_meg=False, exclude=[])
    starts = np.linspace(60, raw.n_times / FS - 70, 10)
    rms = np.median([raw.get_data(picks=meg, start=int(t * FS), stop=int((t + 10) * FS)).std(axis=1)
                     for t in starts], axis=0)
    bad = (rms < np.median(rms) / FLAT_RATIO) | (rms > np.median(rms) * SATURATED_RATIO)
    return tuple(raw.ch_names[meg[j]] for j in np.where(bad)[0])


ADAPTOR = Karunathilake2025Adaptor
