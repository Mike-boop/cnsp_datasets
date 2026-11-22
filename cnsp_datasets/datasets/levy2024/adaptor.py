from __future__ import annotations

import glob
import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from scipy.io import loadmat

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS, ENV_FS = 1024, 100
FEATURE = "envelope"  # the authors' 100 Hz speech envelope (no audio shared)
N_SCALP = 64
EOG = ["EXG1", "EXG3", "EXG4"]  # EXG5/EXG6 (mastoids, the reference) and GSR1/2 are dropped (notes.md 5, 8)
EVENT_OFFSET = 103  # trlEvents begin = event onset - 103 samples
EVENT_DURATION = 0.3  # event sounds trimmed to 300 ms (paper)
N_EVENTS_LESSONS = 22  # lessons 1-22 have sound-events, 23-30 are quiet
# EEG samples per lesson, identical in the 47 subjects whose trigger codes match stimIdxs (notes.md 3, 7)
LESSON_SAMPLES = {
    1: 42619, 2: 33650, 3: 41754, 4: 40708, 5: 44845, 6: 42584, 7: 31315, 8: 40664, 9: 46082, 10: 33432,
    11: 42189, 12: 53263, 13: 44180, 14: 44156, 15: 45796, 16: 47176, 17: 52555, 18: 46325, 19: 47568, 20: 47996,
    21: 36000, 22: 50897, 23: 48911, 24: 47164, 25: 43877, 26: 41909, 27: 40518, 28: 48103, 29: 41124, 30: 46843,
}
# sub 13: the event schedule of the first 19 trials matches neither the stimIdx nor the trigger-code lesson
EVENTS_UNRELIABLE = {13: range(19)}
NOTES = ("EEG as shipped by the authors: unfiltered (DC; BioSemi 208 Hz anti-alias), 1024 Hz, re-referenced to "
         "the mastoid average (EXG5/EXG6, dropped), microvolts scaled to V; template positions (biosemi64). Trial "
         "sample 0 = the authors' speech-onset marker (trials cut by the authors, no end trigger); envelope sample "
         "0 = trial sample 0 (authors' alignment). No drift correction (not estimable), no offset applied. The "
         "envelope is speech only: in 'events' trials the distractor sounds (annotations) were also heard.")
CONFLICT = (" Trigger codes contradict stimIdxs in this subject: the lesson is taken from stimIdxs (envelope, "
            "condition and decoding agree); the EEG trial was cut by the authors with the length of the trigger-code "
            "lesson and is cropped here to the stimIdx lesson length when longer (notes.md 3).")
EVENTS_NOTE = (" Event annotations as shipped, but their schedule matches neither the stimIdx nor the trigger-code "
               "lesson (notes.md 3): do not trust them.")


class Levy2024Adaptor:
    """
    Levy et al. 2024 (OSF svjqg): attend a virtual teacher in a VR classroom, with distractor sound-events in
    lessons 1-22 ('events') and none in lessons 23-30 ('quiet'). 49 adults (24 AD(H)D, 25 control) x 30 lessons,
    BioSemi 64 + 3 EOG at 1024 Hz, mastoid reference as shipped. Only the authors' 100 Hz speech envelope is shared
    (stimulus `lesson<NN>`, feature `envelope`). Trial = position in recording order; lesson = stimIdxs. Sound-events
    are annotations `distractor_artificial` / `distractor_cough`. Subs 9, 17, 34 miss lessons (kept missing);
    subs 13, 22 have contradictory trigger codes (flagged). See notes.md.
    """

    def __init__(self, download_dir: str):
        paths = glob.glob(os.path.join(download_dir, "dataSub*.mat"))
        self.paths = {int(re.search(r"dataSub(\d+)\.mat$", p).group(1)): p for p in paths}

    def parse(self) -> Iterable[TrialRecord]:
        for sub in sorted(self.paths):
            stim, group = _read_meta(self.paths[sub])
            if int(stim.fs) != ENV_FS:
                raise ValueError(f"subject {sub}: envelope at {stim.fs} Hz")
            lessons = np.atleast_1d(stim.stimIdxs).astype(int).tolist()
            conds = np.atleast_1d(stim.condIdxs).astype(int).tolist()
            missing = sorted(set(LESSON_SAMPLES) - set(lessons))
            for k, (lesson, cond) in enumerate(zip(lessons, conds)):
                n_env = len(np.atleast_1d(stim.data[k]))
                if cond != (lesson <= N_EVENTS_LESSONS) or abs(n_env - LESSON_SAMPLES[lesson] * ENV_FS / FS) > 1:
                    raise ValueError(f"subject {sub} trial {k}: condition or envelope length disagrees with lesson")
                extra = dict(group=group, lesson=lesson, missing_lessons=missing,
                             events_unreliable=k in EVENTS_UNRELIABLE.get(sub, ()))
                yield TrialRecord(
                    subject=sub, session=1, trial=k + 1, condition="events" if cond else "quiet", ns_type="eeg",
                    stimulus=StimulusRecord("audio", f"lesson{lesson:02d}", self._env_loader(sub, k),
                                            is_attended=True, feature_name=FEATURE),
                    neural_data_fn=self._eeg_loader(sub, k, lesson, extra),
                )

    def _env_loader(self, sub: int, k: int) -> Callable[[], dict]:
        """Envelope as shipped (bit-identical across subjects per lesson)."""
        path = self.paths[sub]
        return lambda: {"fs": ENV_FS, "data": np.atleast_1d(_read_meta(path)[0].data[k]).astype(float)[None, :]}

    def _eeg_loader(self, sub: int, k: int, lesson: int, extra: dict) -> Callable[[], mne.io.BaseRaw]:
        path = self.paths[sub]

        def _loader() -> mne.io.BaseRaw:
            eeg = _read_eeg(path)
            d = eeg.data
            codes = np.atleast_1d(d.trialinfo).astype(int) - 100
            conflict = bool(np.any(codes != _read_meta(path)[0].stimIdxs))  # subject-level
            x = d.trial[k]
            start = int(d.sampleinfo[k][0])
            n_shipped = n = x.shape[1]
            if conflict:
                n = min(n, LESSON_SAMPLES[lesson])
            elif n != LESSON_SAMPLES[lesson]:
                raise ValueError(f"subject {sub} trial {k}: {n} samples, lesson {lesson} has {LESSON_SAMPLES[lesson]}")
            labels = [str(c) for c in d.label]
            picks = list(range(N_SCALP)) + [labels.index(c) for c in EOG]
            info = mne.create_info([labels[i] for i in picks], FS, ["eeg"] * N_SCALP + ["eog"] * len(EOG))
            raw = mne.io.RawArray(1e-6 * x[picks, :n], info, verbose="ERROR")  # shipped in µV
            raw.set_montage(mne.channels.make_standard_montage("biosemi64"))
            onsets, types = _events(eeg, start, n_shipped)
            keep = onsets < n / FS
            raw.set_annotations(mne.Annotations(onsets[keep], EVENT_DURATION,
                                                [f"distractor_{t.lower()}" for t in types[keep]]))
            notes = NOTES + (CONFLICT if conflict else "")
            if extra["events_unreliable"] and len(onsets):
                notes += EVENTS_NOTE
            raw.info["description"] = provenance(
                "onset_only", "unknown (not documented; Unity to BioSemi marker at speech onset, trials cut by the "
                "authors)", notes, **extra, trigger_code=int(d.trialinfo[k]),
                trigger_code_conflict=bool(codes[k] != lesson), subject_trigger_codes_inconsistent=conflict,
                bdf_sample_start=start, n_samples_shipped=n_shipped, n_samples=n,
                n_events_cropped=int((~keep).sum()), reference="average of mastoids EXG5/EXG6 (as shipped)",
                eog=EOG, dropped=["EXG5", "EXG6", "GSR1", "GSR2"], units_as_shipped="uV",
                positions="template (biosemi64)")
            return raw
        return _loader


def _events(eeg, start: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Sound-event onsets (s, re trial start) and types within the shipped trial."""
    trl = np.atleast_2d(eeg.trlEvents)
    onsets = np.array([int(b) for b in trl[:, 0]]) + EVENT_OFFSET - start
    inside = (onsets >= 0) & (onsets < n)
    return onsets[inside] / FS, np.array([str(t) for t in trl[inside, 3]])


@lru_cache(maxsize=2)
def _read_meta(path: str) -> tuple:
    """(stim struct, participant group) of one subject (small)."""
    m = loadmat(path, squeeze_me=True, struct_as_record=False, variable_names=["stim", "participant"])
    return m["stim"], str(m["participant"].group)


@lru_cache(maxsize=1)
def _read_eeg(path: str):
    """eeg struct of one subject (~1.5 GB as float64)."""
    return loadmat(path, squeeze_me=True, struct_as_record=False, variable_names=["eeg"])["eeg"]


ADAPTOR = Levy2024Adaptor
