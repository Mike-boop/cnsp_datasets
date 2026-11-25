from __future__ import annotations

import glob
import logging
import os
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple

import numpy as np
from mne import Annotations
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray, read_raw_brainvision

from cnsp_datasets.config import get_path
from cnsp_datasets.datasets.bentum2023.drift import estimate_drift_from_xml, file_starts_ms, wav_duration_ms, wav_index
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import to_audio_clock
from cnsp_datasets.standardise.iohelpers import mark_bads, read_wav, textgrid
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

log = logging.getLogger(__name__)

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

# corpus field in the XML -> (adaptor argument, config path name) giving that corpus' audio directory
CORPUS_DIRS = {
    "IFADV": ("ifadv_dir", "CNSP_IFADV_DIR"),
    "CGN": ("sdc_dir", "CNSP_CGN_DIR"),
}
OVERLAP_WARN_S = 0.02  # TextGrid intervals overlapping the previous one by more than this are logged as warnings


class Bentum2023Adapter(BaseAdaptor):
    """
    Adapter for the Dutch EEG Speech Register Corpus (Bentum et al., 2023).

    The EEG is public, but the stimuli are not: they come from the IFADV corpus
    (spontaneous dialogues, DVA*.wav) and the Spoken Dutch Corpus / CGN (news and
    read-aloud stories, fn*.wav), which must be obtained separately. Their locations
    are passed as ifadv_dir / sdc_dir or configured as the paths CNSP_IFADV_DIR /
    CNSP_CGN_DIR (environment variable or paths.json; cnsp_datasets.config.get_path).
    Blocks whose corpus directory is not configured are skipped (logged).

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
        "textgrid" (word/phone tiers per speaker, in block time; an interval overlapping the
        previous one in its tier starts at the previous one's end, logged).
      - The stimulus name is the block's wav_filename without the "_60db" suffix. IFADV blocks
        are the corpus files (DVA7B.wav). CGN blocks are built here from the corpus fn*.wav
        files listed in the block's fids, as the authors did: news blocks (N02003_4) join
        12-15 files with 900 ms of silence, two-file stories (fn001124_fn001125) join them
        directly. The gaps come from the XML (fid_st / fid_et; exactly 900 or 0 ms in every
        block). The XML's file onsets are the wav durations rounded to whole ms, which adds up to
        ~2 ms over a news block, so file onsets (for the word timings) and block durations (for
        the drift) are taken from the wav files instead. Participants heard level-normalised _60db
        versions, whereas this loads the unnormalised files.

    Clock drift: the EEG clock runs about 30-35 ppm slow relative to the audio (about 30 ms
    over a 900 s dialogue), varying by about 6 ppm between recordings. With
    drift_correction="recording" (default), drift is estimated per .vhdr recording from all
    blocks' onset/offset markers (see drift.py and drift_analysis.ipynb), and each block's EEG
    is resampled by quintic spline interpolation onto the audio clock at 1000 Hz, anchored at
    the onset marker. "global" uses the median drift across recordings; None disables it.
    marker_offset fixes the constant end-marker offset used in the estimate (in samples;
    estimated from the corpus if None).

    All blocks are included. The authors rated some "doubtfull" or "bad" and excluded them from
    their analyses; pass exclude_usability=("doubtfull", "bad") to skip them.
    """

    def __init__(
        self,
        download_dir: str,
        ifadv_dir: str | None = None,
        sdc_dir: str | None = None,
        exclude_usability: Iterable[str] = (),
        drift_correction: str | None = "recording",
        marker_offset: float | None = None,
    ):
        super().__init__(download_dir)
        self.root = download_dir
        self.xml_root = self.path("XML_INFO")

        given = {"IFADV": ifadv_dir, "CGN": sdc_dir}
        dirs = {corpus: given[corpus] or get_path(name) for corpus, (_, name) in CORPUS_DIRS.items()}
        self.corpus_dirs = {corpus: str(d) if d else None for corpus, d in dirs.items()}
        self.exclude_usability = set(exclude_usability)

        self.choice("drift_correction", drift_correction, DRIFT_MODES)
        self.drift_correction = drift_correction
        corpus_dirs = tuple(sorted((k, v) for k, v in self.corpus_dirs.items() if v))
        self.drift = estimate_drift_from_xml(self.xml_root, marker_offset, corpus_dirs) if drift_correction else None

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
                        data_fn=self._make_audio_loader(block),
                        is_attended=True,
                        feature_name="audio",
                    ),
                ]
                words_path = os.path.join(pp_dir, "WORDS", f"{block['name']}.xml")
                if os.path.exists(words_path):
                    stimuli.append(StimulusRecord(
                        modality="audio",
                        name=name,
                        data_fn=self._make_textgrid_loader(words_path, block),
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
            log.warning("bentum2023: skipped %d %s: %s", n, unit, reason)

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
            # names as in the recording header, renamed like the channels; unknown names are logged
            mark_bads(out, [CHANNEL_RENAMES.get(ch, ch) for ch in bads], strict=False)

            # EEG sample positions -> audio-clock seconds
            eeg_fs = sfreq * (1 + drift)
            onsets = [(s - start) / eeg_fs for s, _ in artefacts]
            durations = [(e - s) / eeg_fs for s, e in artefacts]
            if onsets:
                out.set_annotations(Annotations(onsets, durations, "BAD_artefact"))
            return out
        return _loader

    def _make_audio_loader(self, block: Dict[str, str]) -> Callable[[], Dict[str, Any]]:
        """The block's audio: one corpus file, or CGN files joined with the gaps given by the XML."""
        corpus = block["corpus"]
        fids = self._split(block["fids"])
        starts = [int(v) for v in self._split(block["fid_st"])]
        ends = [int(v) for v in self._split(block["fid_et"])]
        gaps_s = [(s - e) / 1000 for e, s in zip(ends[:-1], starts[1:])]  # EEG samples at 1 kHz: 0 or 0.9 s

        def _loader() -> Dict[str, Any]:
            index = self._get_audio_index(corpus)
            parts, fs = [], None
            for i, fid in enumerate(fids):
                if fid not in index:
                    raise FileNotFoundError(f"'{fid}.wav' ({corpus}) not found under {self.corpus_dirs[corpus]!r}")
                x, fs_i = read_wav(index[fid])
                if fs is not None and fs_i != fs:
                    raise ValueError(f"{block['name']}: sample rates differ between {fids}")
                fs = fs_i
                x = x.mean(axis=0)  # dialogues: one speaker per channel, mixed; mono files unchanged
                if i:
                    parts.append(np.zeros(round(gaps_s[i - 1] * fs), dtype=np.float32))
                parts.append(x)
            return {"fs": int(fs), "data": np.concatenate(parts)[None, :]}
        return _loader

    def _make_textgrid_loader(self, words_path: str, block: Dict[str, str]) -> Callable[[], str]:
        def _loader() -> str:
            tiers: Dict[str, List[Tuple[float, float, str]]] = defaultdict(list)
            # word st/et are relative to the word's file; the file's onset in the block comes from the exact
            # durations of the files before it (the XML's fid_st are rounded to whole ms per file)
            starts = dict(zip((int(v) for v in self._split(block["fid_st"])), self._file_starts_ms(block) / 1000))

            for word in ET.parse(words_path).getroot():
                sid = word.findtext("sid")
                file_offset = starts[int(word.findtext("fid_st_sample"))]
                w_on = file_offset + float(word.findtext("st"))
                w_off = file_offset + float(word.findtext("et"))
                w_st_sample = int(word.findtext("st_sample"))

                tiers[f"words-{sid}"].append((w_on, w_off, word.findtext("word_utf8_nocode")))

                for ph in word.iterfind("phoneme_word/phoneme"):
                    tiers[f"phones-{sid}"].append((w_on + (int(ph.findtext("st_sample")) - w_st_sample) / 1000,
                                                   w_on + (int(ph.findtext("et_sample")) - w_st_sample) / 1000,
                                                   ph.findtext("ipa")))

            return textgrid({name: trim_overlaps(ivs, f"{block['name']} {name}")
                             for name, ivs in sorted(tiers.items())})
        return _loader

    # ----------------------------- Helpers -----------------------------

    def _skip_reason(self, block: Dict[str, str]) -> str | None:
        if block["usability"] in self.exclude_usability:
            return f"usability '{block['usability']}'"
        if not self.corpus_dirs.get(block["corpus"]):
            arg, name = CORPUS_DIRS[block["corpus"]]
            return f"no audio directory configured for corpus {block['corpus']} ({arg} or {name})"
        missing = [
            fn for fn in (block["vhdr_fn"], block["vmrk_fn"], block["eeg_fn"])
            if not os.path.exists(os.path.join(self.root, fn))
        ]
        if missing:
            return "EEG files missing from download"
        return None

    def _participant_dirs(self) -> List[str]:
        dirs = glob.glob(os.path.join(self.xml_root, "PP*"))  # sorted below
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
        return wav_index(self.corpus_dirs[corpus])

    def _file_starts_ms(self, block: Dict[str, str]):
        """Onsets of the block's files in its concatenated audio (ms), and the audio's end (see drift.file_starts_ms)."""
        index = self._get_audio_index(block["corpus"])
        durations = [wav_duration_ms(index[f]) for f in self._split(block["fids"])]
        return file_starts_ms(durations, [int(v) for v in self._split(block["fid_st"])],
                              [int(v) for v in self._split(block["fid_et"])])


def trim_overlaps(intervals: List[Tuple[float, float, str]], label: str = "tier") -> List[Tuple[float, float, str]]:
    """
    Intervals sorted by onset; one that starts before the previous one ends starts at that end instead (dropped
    if nothing is left), as a TextGrid tier cannot overlap. Overlaps above OVERLAP_WARN_S are logged as warnings.
    """
    out: List[Tuple[float, float, str]] = []
    for a, b, text in sorted(intervals, key=lambda iv: (iv[0], iv[1])):
        if out and a < out[-1][1]:
            overlap = out[-1][1] - a
            (log.warning if overlap > OVERLAP_WARN_S else log.debug)(
                "%s: %r overlaps the previous interval by %.3f s; trimmed", label, text, overlap)
            a = out[-1][1]
            if a >= b:
                continue
        out.append((a, b, text))
    return out


@lru_cache(maxsize=4)
def _read_brainvision(vhdr_path: str) -> BaseRaw:
    return read_raw_brainvision(vhdr_path, preload=False, verbose="ERROR")


ADAPTOR = Bentum2023Adapter
