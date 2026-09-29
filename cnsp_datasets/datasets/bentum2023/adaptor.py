from __future__ import annotations

import json
import os
import glob
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

import numpy as np
from scipy.io import wavfile
from mne import Annotations
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray, read_raw_brainvision

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid
from cnsp_datasets.datasets.bentum2023.drift import estimate_drift_from_xml, to_audio_clock


CONFIG_PATH = Path(__file__).with_name("config.json")

DRIFT_MODES = ("recording", "global", None)

# exp_type code in the XML -> condition label
CONDITIONS = {
    "ifadv": "spontaneous-dialogue",
    "k": "news-broadcast",
    "o": "read-aloud-story",
}

# Recorded against the left mastoid (online reference, so not in the data). Four cap
# positions were used for EOG: FT10 has no suffix in the header, but it is the
# right-canthus partner of FT9 (the authors' channel_names.txt merges the two
# into a bipolar HEOG, as it does Fp1/Oz into VEOG).
CHANNEL_RENAMES = {
    "Fp1_EOG_V_high": "VEOG_high",
    "Oz_EOG_V_low": "VEOG_low",
    "FT9_EOG_H_left": "HEOG_left",
    "FT10": "HEOG_right",
    "TP10_RM": "A2",
}
EOG_CHANNELS = ["VEOG_high", "VEOG_low", "HEOG_left", "HEOG_right"]
MISC_CHANNELS = ["A2"]  # right mastoid, treated as an EXG electrode

# corpus field in the XML -> config key holding that corpus' audio directory
CORPUS_DIRS = {
    "IFADV": "ifadv_dir",
    "CGN": "sdc_dir",
}


class Bentum2023Adapter:
    """
    Adapter for the Dutch EEG Speech Register Corpus (Bentum et al., 2023).

    The EEG is public, but the stimuli are not: they come from the IFADV corpus
    (spontaneous dialogues, DVA*.wav) and the Spoken Dutch Corpus / CGN (news and
    read-aloud stories, fn*.wav), which must be obtained separately. Their locations
    are read from config.json next to this file ("ifadv_dir", "sdc_dir"), or can be
    passed directly. Blocks whose corpus directory is not configured are skipped.

    Expected layout:
      <download_dir>/
        ├─ EEG/pp*.vhdr|vmrk|eeg          (one BrainVision recording per session, 1000 Hz)
        └─ XML_INFO/PP<n>/
             ├─ sessions.xml             (session order per experiment)
             ├─ blocks.xml               (block sample ranges, audio onsets, artefacts)
             └─ WORDS/<block>.xml        (word + phoneme alignments)

    Each experimental block becomes one trial:
      - EEG is cropped to the block's [st_sample, et_sample) range, so t=0 is audio onset,
        and trial is the block number (presentation order, which varies across participants).
      - 26 scalp channels, 4 EOG channels (VEOG_high/low, HEOG_left/right) and the right
        mastoid (A2, type misc), all referenced to the left mastoid.
      - Channels flagged in rejected_channels are marked bad; artefact spans become
        BAD_artefact annotations.
      - Stimuli: "audio" (mono, the dialogue's two speaker channels mixed) and
        "textgrid" (word/phone tiers per speaker, in block time).
      - The stimulus name is the block's wav_filename without the "_60db" suffix, and the
        audio is loaded from <name>.wav in the corpus directory. For IFADV these are the
        corpus files (DVA7B.wav). News and multi-file story blocks (N02003_4.wav,
        fn001124_fn001125.wav) were built by the authors by concatenating CGN fn*.wav
        files and must be re-synthesised into sdc_dir. Their layout is identical for every
        participant; the offsets are in the XML fid_st / fid_et fields. Participants heard
        level-normalised _60db versions, whereas this loads the unnormalised files.

    Clock drift: the EEG clock runs about 30-35 ppm slow relative to the audio (about 30 ms
    over a 900 s dialogue), varying by about 6 ppm between recordings. With
    drift_correction="recording" (default), drift is estimated per .vhdr recording from all
    blocks' onset/offset markers (see drift.py and drift_analysis.ipynb), and each block's EEG
    is resampled by quintic spline interpolation onto the audio clock at 1000 Hz, anchored at
    the onset marker. "global" uses the median drift across recordings; None disables it.
    marker_offset fixes the constant end-marker offset used in the estimate (in samples;
    estimated from the corpus if None).

    Blocks rated "doubtfull" or "bad" were excluded from the authors' analyses and are
    skipped by default (see exclude_usability).
    """

    def __init__(
        self,
        download_dir: str,
        ifadv_dir: str | None = None,
        sdc_dir: str | None = None,
        exclude_usability: Iterable[str] = ("doubtfull", "bad"),
        drift_correction: str | None = "recording",
        marker_offset: float | None = None,
    ):
        self.root = download_dir
        self.xml_root = os.path.join(download_dir, "XML_INFO")
        if not os.path.isdir(self.xml_root):
            raise FileNotFoundError(f"No XML_INFO directory found under {download_dir!r}")

        config = self._read_config()
        self.corpus_dirs = {
            "IFADV": ifadv_dir or config.get("ifadv_dir") or None,
            "CGN": sdc_dir or config.get("sdc_dir") or None,
        }
        self.exclude_usability = set(exclude_usability)

        if drift_correction not in DRIFT_MODES:
            raise ValueError(f"drift_correction must be one of {DRIFT_MODES}, got {drift_correction!r}")
        self.drift_correction = drift_correction
        self.drift = estimate_drift_from_xml(self.xml_root, marker_offset) if drift_correction else None

        # corpus -> {wav stem: full path}, built lazily per corpus
        self._audio_index: Dict[str, Dict[str, str]] = {}

    # ----------------------------- Public API -----------------------------

    def parse(self) -> Iterable[TrialRecord]:
        skipped: Counter = Counter()

        for pp_dir in self._participant_dirs():
            blocks_path = os.path.join(pp_dir, "blocks.xml")
            if not (os.path.exists(blocks_path) and os.path.exists(os.path.join(pp_dir, "sessions.xml"))):
                skipped["participant XML missing from download"] += 1
                continue
            sessions = self._read_session_numbers(pp_dir)

            for block in self._read_xml_list(blocks_path):
                reason = self._skip_reason(block)
                if reason is not None:
                    skipped[reason] += 1
                    continue

                name = Path(block["wav_filename"]).stem.removesuffix("_60db")
                stimuli = [
                    StimulusRecord(
                        modality="audio",
                        name=name,
                        data_fn=self._make_audio_loader(block["corpus"], name),
                        is_attended=True,
                        feature_name="audio",
                    ),
                ]
                words_path = os.path.join(pp_dir, "WORDS", f"{block['name']}.xml")
                if os.path.exists(words_path):
                    stimuli.append(StimulusRecord(
                        modality="audio",
                        name=name,
                        data_fn=self._make_textgrid_loader(words_path, int(block["st_sample"])),
                        is_attended=True,
                        feature_name="textgrid",
                    ))

                yield TrialRecord(
                    subject=int(block["pp_id"]),
                    session=sessions[block["exp_type"]],
                    trial=int(block["block_number"]),
                    condition=CONDITIONS[block["exp_type"]],
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=self._make_eeg_loader(block),
                )

        for reason, n in sorted(skipped.items()):
            unit = "participants" if reason.startswith("participant") else "blocks"
            print(f"[Bentum2023Adapter] skipped {n} {unit}: {reason}")

    # ----------------------------- Lazy loaders -----------------------------

    def _make_eeg_loader(self, block: Dict[str, str]) -> Callable[[], BaseRaw]:
        vhdr_path = os.path.join(self.root, block["vhdr_fn"])
        # XML sample numbers are BrainVision marker positions, which are 1-based
        start = int(block["st_sample"]) - 1
        stop = int(block["et_sample"]) - 1
        bads = self._split(block["rejected_channels"])
        drift = self.drift.drift(block["vhdr_fn"], self.drift_correction) if self.drift else 0.0
        # clip artefact spans to the block
        artefacts = [
            (max(int(s) - 1, start), min(int(e) - 1, stop))
            for s, e in zip(self._split(block["artefact_st"]), self._split(block["artefact_et"]))
        ]
        artefacts = [(s, e) for s, e in artefacts if s < e]

        def _loader() -> BaseRaw:
            raw = _read_brainvision(vhdr_path)
            if stop > raw.n_times:
                raise ValueError(
                    f"{block['name']}: block ends at sample {stop} but {vhdr_path} only has "
                    f"{raw.n_times} samples (incomplete download?)"
                )
            sfreq = raw.info["sfreq"]

            info = raw.info.copy()
            data = to_audio_clock(raw.get_data(start=start, stop=stop), drift)
            out = RawArray(data, info, verbose="ERROR")
            if drift:
                out.info["description"] = (
                    f"Resampled onto the audio clock: drift {drift * 1e6:.2f} ppm "
                    f"({self.drift_correction}), marker offset {self.drift.marker_offset:.2f} samples"
                )

            out.rename_channels({k: v for k, v in CHANNEL_RENAMES.items() if k in out.ch_names})
            out.set_channel_types({
                **{ch: "eog" for ch in EOG_CHANNELS if ch in out.ch_names},
                **{ch: "misc" for ch in MISC_CHANNELS if ch in out.ch_names},
            }, on_unit_change="ignore")  # misc unit label becomes NA; data stay in volts
            # 10-20 positions for the scalp channels only: MNE applies montages to EEG-typed
            # channels, so EOG (placed around the eye, not at their cap positions) and A2 are
            # left unpositioned. verbose silences the notice about skipping A2.
            out.set_montage(make_standard_montage("standard_1020"), on_missing="raise", verbose="ERROR")
            out.info["bads"] = [ch for ch in bads if ch in out.ch_names]

            # EEG sample positions -> audio-clock seconds
            eeg_fs = sfreq * (1 + drift)
            onsets = [(s - start) / eeg_fs for s, _ in artefacts]
            durations = [(e - s) / eeg_fs for s, e in artefacts]
            if onsets:
                out.set_annotations(Annotations(onsets, durations, "BAD_artefact"))
            return out
        return _loader

    def _make_audio_loader(self, corpus: str, name: str) -> Callable[[], Dict[str, Any]]:
        def _loader() -> Dict[str, Any]:
            index = self._get_audio_index(corpus)
            if name not in index:
                raise FileNotFoundError(
                    f"Audio '{name}.wav' ({corpus}) not found under {self.corpus_dirs[corpus]!r}"
                )
            fs, x = wavfile.read(index[name])
            x = x.astype(np.float32) / np.iinfo(x.dtype).max if x.dtype.kind == "i" else x.astype(np.float32)
            if x.ndim == 2:
                x = x.mean(axis=1)  # dialogues: one speaker per channel
            return {"fs": int(fs), "data": x[None, :]}
        return _loader

    def _make_textgrid_loader(self, words_path: str, st_sample: int) -> Callable[[], str]:
        def _loader() -> str:
            tiers: Dict[str, Dict[str, List]] = defaultdict(lambda: {"item": [], "onset_s": [], "offset_s": []})

            for word in ET.parse(words_path).getroot():
                sid = word.findtext("sid")
                # st/et are relative to the word's audio file; shift to block time
                file_offset = (int(word.findtext("fid_st_sample")) - st_sample) / 1000
                w_on = file_offset + float(word.findtext("st"))
                w_off = file_offset + float(word.findtext("et"))
                w_st_sample = int(word.findtext("st_sample"))

                tier = tiers[f"words-{sid}"]
                tier["item"].append(word.findtext("word_utf8_nocode"))
                tier["onset_s"].append(w_on)
                tier["offset_s"].append(w_off)

                for ph in word.iterfind("phoneme_word/phoneme"):
                    tier = tiers[f"phones-{sid}"]
                    tier["item"].append(ph.findtext("ipa"))
                    tier["onset_s"].append(w_on + (int(ph.findtext("st_sample")) - w_st_sample) / 1000)
                    tier["offset_s"].append(w_on + (int(ph.findtext("et_sample")) - w_st_sample) / 1000)

            return multi_tier_dict_to_textgrid(dict(sorted(tiers.items())))
        return _loader

    # ----------------------------- Helpers -----------------------------

    def _skip_reason(self, block: Dict[str, str]) -> str | None:
        if block["usability"] in self.exclude_usability:
            return f"usability '{block['usability']}'"
        if not self.corpus_dirs.get(block["corpus"]):
            return f"no audio directory configured for corpus {block['corpus']} ({CORPUS_DIRS[block['corpus']]})"
        missing = [
            fn for fn in (block["vhdr_fn"], block["vmrk_fn"], block["eeg_fn"])
            if not os.path.exists(os.path.join(self.root, fn))
        ]
        if missing:
            return "EEG files missing from download"
        return None

    def _participant_dirs(self) -> List[str]:
        dirs = glob.glob(os.path.join(self.xml_root, "PP*"))
        return sorted(dirs, key=lambda d: int(os.path.basename(d)[2:]))

    def _read_session_numbers(self, pp_dir: str) -> Dict[str, int]:
        sessions = self._read_xml_list(os.path.join(pp_dir, "sessions.xml"))
        return {s["exp_type"]: int(s["session_number"]) for s in sessions}

    @staticmethod
    def _read_xml_list(path: str) -> List[Dict[str, str]]:
        return [{c.tag: (c.text or "").strip() for c in el} for el in ET.parse(path).getroot()]

    @staticmethod
    def _split(field: str) -> List[str]:
        return [v for v in field.split(",") if v and v != "NA"]

    def _get_audio_index(self, corpus: str) -> Dict[str, str]:
        if corpus not in self._audio_index:
            paths = glob.glob(os.path.join(self.corpus_dirs[corpus], "**", "*.wav"), recursive=True)
            self._audio_index[corpus] = {Path(p).stem: p for p in paths}
        return self._audio_index[corpus]

    @staticmethod
    def _read_config() -> Dict[str, Any]:
        if not CONFIG_PATH.exists():
            return {}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


@lru_cache(maxsize=4)
def _read_brainvision(vhdr_path: str) -> BaseRaw:
    return read_raw_brainvision(vhdr_path, preload=False, verbose="ERROR")


ADAPTOR = Bentum2023Adapter
