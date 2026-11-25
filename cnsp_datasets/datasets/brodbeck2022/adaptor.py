from __future__ import annotations

import glob
import os
import re
from functools import lru_cache
from typing import Iterable

import numpy as np
import pandas as pd

from cnsp_datasets.datasets.brodbeck2022 import ndvar
from cnsp_datasets.datasets.simon_base.common import REFERENCE, crop_meg, read_raw
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1000
TASK = "Appleseed"
ONSET_CODE = 162  # segment onset trigger (MISC 003); 167 = offset
JITTER_MS = 10    # ~10 ms trigger-to-trigger quantisation (notes.md section 7)
TRIGGER_TYPE = ("software (inferred: ~10 ms quantised trigger intervals, notes.md section 7; not documented; TTL "
                "lines recorded by the KIT system)")
DRIFT_PPM = 3.4   # estimated in the clean subject group (95% -14..+18), not corrected (notes.md section 7)
NOTES = ("Onset = trigger 162 (events.tsv onset), no offset or drift correction (no drift measurable: +3.4 ppm, "
         "95% -14..+18, in the clean subject group). No audio is shipped (copyright) and there is no stimtrack: the "
         "absolute audio latency after the trigger is unknown. Features from the shipped 1 kHz gammatone "
         "spectrogram (20-5000 Hz, 256 ERB bands, linear RMS amplitude, negative values clipped at 0); each "
         "sample summarises audio [t, t+10) ms, so the features lead the audio by ~5 ms (not shifted) and are "
         "10 ms shorter than the stimulus. MISC lines (trigger lines, idle) and STI 014 dropped.")
FLAGS = {
    **{(sub, seg): "Trigger interval 1.265 s longer than the shipped stimulus (earliest three subjects); the MEG "
                   "places the shipped stimulus at the onset trigger, the extra time lies after its end."
       for sub in (4, 5, 6) for seg in (6, 7)},
    (11, 6): "Restart of segment 6: an earlier false start (onset trigger at 1510.677 s, no offset) may have "
             "played its beginning once before.",
}


class Brodbeck2022Adaptor(BaseAdaptor):
    """
    Appleseed audiobook MEG (Brodbeck et al. 2022, OpenNeuro ds007870): 12 subjects, 11 consecutive excerpts of
    "The Botany of Desire" in one KIT 157-channel recording each (1000 Hz, T); sub-04/05 heard excerpt 11b
    instead of 11. Trial = segment 1-11 in presentation order. No audio: stimuli are the broadband envelope
    (sum over bands) and the 256-band gammatone spectrogram from stimuli/*-gammatone1000.pickle, plus the
    shipped TextGrids (words, phones). The Tone task is skipped. See notes.md.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)

    def parse(self) -> Iterable[TrialRecord]:
        for meg_dir in sorted(glob.glob(os.path.join(self.download_dir, "sub-[0-9]*", "meg"))):
            sub = int(re.search(r"sub-(\d+)", meg_dir).group(1))
            stem = os.path.join(meg_dir, f"sub-{sub:02d}_task-{TASK}")
            events = pd.read_csv(f"{stem}_events.tsv", sep="\t", dtype={"stimulus": str})
            onsets = events[events.value == ONSET_CODE]
            for seg, (onset, stim) in enumerate(zip(onsets.onset, onsets.stimulus), 1):
                name = f"appleseed-{stim.zfill(2)}"
                description = provenance(
                    "sw_trigger", TRIGGER_TYPE, NOTES + (" " + FLAGS[sub, seg] if (sub, seg) in FLAGS else ""),
                    drift_ppm=DRIFT_PPM, jitter_ms=JITTER_MS, onset_s=float(onset), stimulus_file=stim,
                    flagged=(sub, seg) in FLAGS, units_as_shipped="T", reference=REFERENCE)
                yield TrialRecord(
                    subject=sub, session=1, trial=seg, condition="appleseed", ns_type="meg",
                    stimulus=self._stimuli(name, stim),
                    neural_data_fn=self._meg_loader(stem, onset, stim, description),
                )

    def _path(self, stim: str, suffix: str) -> str:
        return os.path.join(self.download_dir, "stimuli", f"{stim}{suffix}")

    def _stimuli(self, name: str, stim: str) -> list:
        pickle_path, textgrid = self._path(stim, "-gammatone1000.pickle"), self._path(stim, ".TextGrid")

        def _envelope():
            x, _ = _gammatone(pickle_path)
            return {"fs": FS, "data": x.sum(axis=0)[None].astype(np.float32)}

        def _spectrogram():
            x, freqs = _gammatone(pickle_path)
            return {"fs": FS, "data": x.astype(np.float32), "frequencies_hz": freqs}

        def _textgrid():
            with open(textgrid, encoding="utf-8") as f:
                return f.read()

        return [StimulusRecord("audio", name, _envelope, True, feature_name="envelope"),
                StimulusRecord("audio", name, _spectrogram, True, feature_name="gammatone"),
                StimulusRecord("audio", name, _textgrid, True, feature_name="textgrid")]

    def _meg_loader(self, stem: str, onset: float, stim: str, description: str):
        def _loader():
            raw = read_raw(f"{stem}_split-01_meg.fif", FS)  # opening split-01 joins split-02; bads as in channels.tsv
            return crop_meg(raw, onset * FS, _duration(self._path(stim, ".TextGrid")), description)

        return _loader


@lru_cache(maxsize=1)
def _gammatone(path: str) -> tuple[np.ndarray, np.ndarray]:
    """(bands x time) linear gammatone amplitude clipped at 0, centre frequencies (Hz), checked at 1 kHz."""
    nd = ndvar.load(path).state
    freq, time = (d.state for d in nd["dims"])
    if time["tstep"] != 1 / FS or time["tmin"] != 0 or nd["x"].shape != (len(freq["values"]), time["nsamples"]):
        raise ValueError(f"{path}: unexpected NDVar layout")
    return np.maximum(nd["x"], 0), np.asarray(freq["values"])


def _duration(textgrid: str) -> int:
    """Stimulus length in samples (TextGrid xmax = stimulus duration)."""
    with open(textgrid, encoding="utf-8") as f:
        xmax = float(re.search(r"^xmax = ([\d.]+)", f.read(), re.M).group(1))
    return int(round(xmax * FS))


ADAPTOR = Brodbeck2022Adaptor
