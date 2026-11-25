from __future__ import annotations

import csv
import glob
import logging
import os
from typing import Callable, Iterable

import numpy as np
import pandas as pd
import soundfile
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from scipy.io import loadmat

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import mark_bads, read_wav, textgrid
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

log = logging.getLogger(__name__)

SENT_DIR = os.path.join("sourcedata", "stimuli", "audio_files_segmented_by_sentence")
WORDS = os.path.join("sourcedata", "annotation", "lppHK_timing_word_information.xlsx")
AUDIO_FS, EEG_FS = 44100, 1000
PARTS = (1, 2, 3, 4)
CHANNEL_TYPES = {"M1": "misc", "M2": "misc", "VEO": "eog", "HEO": "eog", "EKG": "ecg", "EMG": "emg"}
# HK005: 1.065 was cut short by 1.066 and 1.067-1.070 were never played; the trial ends at the 1.066 trigger (notes 6)
STOP_AT = {("HK005", 1): "1.066"}
STOP_NOTE = "Trial ends at the 1.066 trigger: 1.065 was cut 191 ms short and 1.067-1.070 were never played."
WEAK_TRACKING = {"HK037", "HK042"}  # no clear envelope tracking at any lag (notes 7)
BAD_CHANNELS = {"HK050": ["T8"]}  # mV artefact for the first 85 s of Part 1, near-flat after, 211 mV DC (notes 15)
QUALITY = {("HK050", 1): "suspect: T8 carries a 1-40 Hz SD of ~3.4 mV for the first 85 s (marked bad); with T8 in "
                         "an average reference the trial looks misaligned (spurious -0.44 s peak). Without T8 the "
                         "alignment is normal (envelope-EEG peak +0.21 s)."}
WINDOW_S = (-0.3, 1.5)  # accepted trigger time relative to the previous trigger + previous sentence duration
NOTES = ("Presented sentence by sentence (STIM2, one trigger per sentence). EEG kept continuous and untouched from the "
         "Part's first sentence trigger; the stimulus is built per participant and Part by placing each sentence wav "
         "(mono (L+R)/2 of the stereo file) at its own trigger on a silent track, so the ~8.5 ms inter-sentence gaps "
         "and any pauses are silence; where a trigger came before the previous sentence ended, that sentence is cut "
         "at the trigger. No drift correction (within-sentence ~117 ppm, <1 ms per sentence); sentence-onset jitter "
         "~7 ms SD. Online reference unknown (inferred near CZ/CPZ; the BIDS 'Average' is wrong); positions are "
         "template. Word boundaries are mostly interpolated within sentences (upstream annotation).")
WEAK_NOTE = "No clear speech tracking at any lag (explorer check); kept and flagged."
WORD_NOTE = ("words: upstream onset/offset (interpolated within most sentences) placed at the sentence trigger; "
             "5 words with offset < onset dropped; sentences: the placed sentence wavs.")


class Momenian2024Adaptor(BaseAdaptor):
    """
    Momenian et al. 2024, Le Petit Prince Hong Kong, EEG part (OpenNeuro ds004718 v1.1.2): 51 older Cantonese
    listeners hear the story in four ~5-min Parts, one sentence wav at a time (535 sentences, one trigger each).
    Neuroscan/Curry, 62 scalp channels + M1/M2 (misc), VEO/HEO, EKG/EMG in four files, 1000 Hz, as recorded.

    Trial = Part (1-4). EEG = the continuous recording from the Part's first sentence trigger to the end of its last
    sentence. Stimulus `HK<id>_part<p>` (per participant): the sentence wavs placed at their triggers on a silent
    44.1 kHz track (`audio`), plus a TextGrid (`words`, `sentences`). Parts past the end of a truncated .fdt are
    skipped. See notes.md.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = download_dir
        self.sentences = {p: _sentence_table(download_dir, p) for p in PARTS}
        self.words = _word_table(download_dir, self.sentences)
        with open(self.path("participants.tsv"), newline="") as f:
            self.participants = {r["participant_id"][4:]: r for r in csv.DictReader(f, delimiter="\t")}

    def parse(self) -> Iterable[TrialRecord]:
        for set_path in sorted(glob.glob(os.path.join(self.root, "sub-HK*", "eeg", "*_eeg.set"))):
            pid = os.path.basename(set_path).split("_")[0][4:]
            eeg = loadmat(set_path, squeeze_me=True, struct_as_record=False, appendmat=False)
            labels = [str(c.labels) for c in np.atleast_1d(eeg["chanlocs"])]
            fdt = os.path.join(os.path.dirname(set_path), str(eeg["datfile"]))
            n_present = os.path.getsize(fdt) // (4 * len(labels))
            if float(eeg["srate"]) != EEG_FS or n_present > int(eeg["pnts"]):
                raise ValueError(f"{set_path}: unexpected sample rate or data size")
            events = [(str(e.type), int(round(float(e.latency))) - 1) for e in np.atleast_1d(eeg["event"])]
            i = 0
            for p in PARTS:
                table = self.sentences[p]
                onsets, i = _match(events, i, table, STOP_AT.get((pid, p)))
                place = _placement(onsets, table["n"].to_numpy()[:len(onsets)], (pid, p) in STOP_AT)
                n_eeg = int(np.ceil(place["n_audio"] * EEG_FS / AUDIO_FS))
                if onsets[0] + n_eeg > n_present:
                    log.info("momenian2024: %s Part %s skipped, .fdt truncated upstream", pid, p)
                    continue
                kept = table.iloc[:len(place["start"])]
                name = f"{pid}_part{p}"
                description = provenance(
                    "sw_trigger", "software (inferred; STIM2 trigger per sentence, paper)",
                    " ".join([NOTES] + [WEAK_NOTE] * (pid in WEAK_TRACKING) + [STOP_NOTE] * ((pid, p) in STOP_AT)),
                    jitter_ms=7.0, validation_tier="low", participant=pid, part=p, first_sentence=kept["id"].iloc[0],
                    last_sentence=kept["id"].iloc[-1], n_sentences=len(kept), first_trigger_sample=int(onsets[0]),
                    cut_sentences=place["cut"], max_cut_ms=place["max_cut_ms"], pauses_ms=place["pauses"],
                    weak_tracking=pid in WEAK_TRACKING, bad_channels=BAD_CHANNELS.get(pid, []),
                    quality=QUALITY.get((pid, p), "ok"),
                    fdt_truncated_upstream=n_present < int(eeg["pnts"]), **self._subject_info(pid),
                    reference="unknown (inferred online reference near CZ/CPZ, Neuroscan default)",
                    external_sensors={"M1": "left mastoid", "M2": "right mastoid"},
                    positions="template (standard_1005; none for F11, F12, FT11, FT12, CB1, CB2)",
                    audio="mono (L+R)/2 of the stereo sentence wavs", annotation=WORD_NOTE,
                )
                yield TrialRecord(
                    subject=int(pid[2:]), session=1, trial=p, condition="clear", ns_type="eeg",
                    stimulus=[StimulusRecord("audio", name, self._audio_loader(p, place), True, "audio"),
                              StimulusRecord("audio", name, self._textgrid_loader(p, place), True, "textgrid")],
                    neural_data_fn=_eeg_loader(fdt, labels, onsets[0], n_eeg, n_present, BAD_CHANNELS.get(pid, []),
                                               description),
                )

    def _subject_info(self, pid: str) -> dict:
        r = self.participants[pid]
        return {"age": int(r["age"]), "sex": r["sex"], "eeg_quiz_accuracy": float(r["EEG_accuracy_quiz_questions"])}

    def _audio_loader(self, p: int, place: dict) -> Callable[[], dict]:
        paths = self.sentences[p]["path"].tolist()

        def _loader() -> dict:
            out = np.zeros(place["n_audio"], np.float32)
            for path, start, n in zip(paths, place["start"], place["n"]):
                out[start:start + n] = _read_mono(path)[:n]
            return {"fs": AUDIO_FS, "data": out[None, :]}
        return _loader

    def _textgrid_loader(self, p: int, place: dict) -> Callable[[], str]:
        table, words = self.sentences[p], self.words[p]

        def _loader() -> str:
            starts, ends = place["start"] / AUDIO_FS, (place["start"] + place["n"]) / AUDIO_FS
            sents = [(a, b, s) for a, b, s in zip(starts, ends, table["id"])]
            word_iv = []
            for k, (a, b) in enumerate(zip(starts, ends)):
                w = words[words["k"] == k].sort_values("on")
                for on, off, text in zip(a + w["on"], a + w["off"], w["word"]):
                    if on < b:
                        word_iv.append((on, min(off, b), text))
            return textgrid({"words": _trim(word_iv), "sentences": _trim(sents)}, xmax=place["n_audio"] / AUDIO_FS)
        return _loader


def _sentence_table(root: str, p: int) -> pd.DataFrame:
    """Sentences of Part p in presentation order: id, trigger code, wav path and length (samples)."""
    paths = sorted(glob.glob(os.path.join(root, SENT_DIR, f"Part {p}", "*.wav")))
    ids = [os.path.basename(x)[:-4] for x in paths]
    n = [soundfile.info(x).frames for x in paths]
    return pd.DataFrame({"id": ids, "code": [i.split(".")[1].lstrip("0") for i in ids], "path": paths, "n": n})


def _word_table(root: str, sentences: dict) -> dict:
    """Per Part: words with onset/offset (s) relative to their sentence wav start, k = sentence index in the Part.

    Upstream onset_all/offset_all are on the concatenated sentence wavs (notes 4); a word belongs to the sentence
    whose wav contains its onset. Words with offset < onset (5) are dropped.
    """
    w = pd.read_excel(os.path.join(root, WORDS))
    w = w[w["offset_all"] >= w["onset_all"]]
    n = np.concatenate([sentences[p]["n"].to_numpy() for p in PARTS])
    edges = np.r_[0, np.cumsum(n)] / AUDIO_FS
    part = np.concatenate([[p] * len(sentences[p]) for p in PARTS])
    first = np.r_[0, np.cumsum([len(sentences[p]) for p in PARTS])]
    g = np.clip(np.searchsorted(edges, w["onset_all"].to_numpy(), side="right") - 1, 0, len(n) - 1)
    w = w.assign(g=g, on=w["onset_all"] - edges[g], off=w["offset_all"] - edges[g])
    return {p: w[part[w["g"]] == p].assign(k=lambda d: d["g"] - first[p - 1]) for p in PARTS}


def _match(events: list, i: int, table: pd.DataFrame, stop: str | None) -> tuple[np.ndarray, int]:
    """Trigger samples of Part sentences in order, searching events from index i; stop = id ending the trial."""
    codes, dur = table["code"].tolist(), table["n"].to_numpy() * EEG_FS / AUDIO_FS
    lo, hi = WINDOW_S[0] * EEG_FS, WINDOW_S[1] * EEG_FS
    for start in range(i, len(events)):
        if events[start][0] != codes[0]:
            continue
        onsets, j = [events[start][1]], start
        for k in range(1, len(codes)):
            expected = onsets[-1] + dur[k - 1]
            j = next((m for m in range(j + 1, len(events)) if events[m][0] == codes[k]
                      and lo <= events[m][1] - expected <= hi), None)
            if j is None:
                break
            onsets.append(events[j][1])
            if table["id"].iloc[k] == stop:
                return np.array(onsets), j
        if len(onsets) == len(codes):
            return np.array(onsets), j
        if len(onsets) > 3:
            raise ValueError(f"sentence {table['id'].iloc[len(onsets)]} trigger not found")
    raise ValueError(f"first sentence {table['id'].iloc[0]} not found")


def _placement(onsets: np.ndarray, n: np.ndarray, stopped: bool) -> dict:
    """Audio sample of each sentence (its trigger), cut at the next trigger; stopped: the last onset ends the trial."""
    start = np.round((onsets - onsets[0]) * AUDIO_FS / EEG_FS).astype(int)
    if stopped:
        start, n, bound = start[:-1], n[:-1], start[1:]
    else:
        bound = np.r_[start[1:], start[-1] + n[-1]]
    end = start + n
    kept = np.minimum(end, bound) - start
    gap_ms = (start[1:] - end[:-1]) * 1000 / AUDIO_FS
    cut_ms = (end - bound)[end > bound] * 1000 / AUDIO_FS
    return {"start": start, "n": kept, "n_audio": int(start[-1] + kept[-1]), "cut": len(cut_ms),
            "max_cut_ms": round(float(cut_ms.max(initial=0)), 1),
            "pauses": [round(float(g)) for g in gap_ms if g > 100]}


def _read_mono(path: str) -> np.ndarray:
    """(L + R) / 2 of a stereo int16 sentence wav, float32."""
    info = soundfile.info(path)
    if info.samplerate != AUDIO_FS or info.subtype != "PCM_16" or info.channels != 2:
        raise ValueError(f"{path}: expected 44.1 kHz stereo int16")
    return read_wav(path)[0].mean(axis=0)


def _eeg_loader(fdt: str, labels: list, i0: int, n: int, n_present: int, bads: list,
                description: str) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        x = np.memmap(fdt, dtype="<f4", mode="r", shape=(n_present, len(labels)))  # sample-major, µV
        keep = [c for c, lab in enumerate(labels) if lab != "TRIGGER"]
        data = 1e-6 * np.asarray(x[i0:i0 + n, keep], dtype=np.float64).T
        names = [labels[c] for c in keep]
        info = create_info(names, EEG_FS, [CHANNEL_TYPES.get(c, "eeg") for c in names])
        raw = RawArray(data, info, verbose="ERROR")
        raw.set_montage(make_standard_montage("standard_1005"), match_case=False, on_missing="ignore",
                       verbose="ERROR")
        mark_bads(raw, bads)
        raw.info["description"] = description
        return raw
    return _loader


def _trim(intervals: list) -> list:
    """Intervals in order without overlaps, as the TextGrid writer of the first pass: one that ends before the
    previous one is dropped, one that starts inside it starts at its end."""
    out, t = [], 0.0
    for a, b, text in intervals:
        if b <= t:
            continue
        out.append((max(a, t), b, text))
        t = b
    return out


ADAPTOR = Momenian2024Adaptor
