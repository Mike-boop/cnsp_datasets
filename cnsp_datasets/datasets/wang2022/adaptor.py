from __future__ import annotations

import glob
import io
import math
import os
from typing import Iterable

import mne
import numpy as np
import pandas as pd
import textgrid
from scipy.io import loadmat, wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

# Fixed presentation order, one row per MEG visit (paper; meas_date of sub-01..06, notes.md section 3)
VISITS = [[1, 11, 31, 41, 56, 46, 36, 26, 16, 6], [21, 51, 2, 12, 32, 42, 47, 37, 7, 17],
          [22, 52, 53, 33, 57, 27, 48, 38, 18, 8], [13, 23, 43, 3, 4, 34, 58, 28, 39, 9],
          [14, 24, 44, 54, 59, 49, 29, 19, 40, 10], [15, 5, 25, 35, 45, 55, 60, 50, 30, 20]]
SKIP = {("06", 58), ("06", 59), ("06", 60)}  # upstream copies of sub-05's runs (notes.md section 2)
NO_BEG = {("08", 16), ("09", 7)}  # no Beg trigger (README): Beg = End - median End-Beg of the story
DRIFT = 500e-6  # MEG clock fast vs the audio clock (MEG response scan, notes.md section 6)
SOUND_DELAY_MS = 39.5  # Beg trigger -> sound at the participant (paper, sound sensor)
FMRI_OFFSET_S = 10.65  # added to the annotation times by the authors (README)
BEG, END = 1, 2  # STI101 codes
BIO = {"BIO001": "bio channel (V), probably one EOG lead (paper mentions EOG; unverified)"}
NOTES = ("MEG as shipped: the authors' tSSS (MaxFilter 2.2.15, 30 s buffer, correlation 0.98) is already applied "
         "in the files OpenNeuro calls raw; no further SSS, no bads marked (reconstructed by SSS). Onset = STI101 "
         "code 1 (software TTL after PsychPortAudio Start) + 39.5 ms sound delay (paper; not applied in the "
         "authors' code). No audio copy: the +500 ppm drift is the dataset value from the MEG envelope response "
         "(trigger fit 482 ppm, 95% CI 420-535), corrected by resampling onto the audio clock. The End trigger has "
         "a per-story scatter of +-20 ms (playback side; not used). line_freq 50 Hz (meg.json says 60). cHPI "
         "293/307/314/321 Hz was on (possibly reduced by tSSS). Participant names/birthdays removed from "
         "subject_info.")


class Wang2022Adaptor:
    """
    SMN4Lang MEG (Wang et al. 2022, OpenNeuro ds004078): 12 subjects, Elekta TRIUX 306-channel MEG at 1000 Hz,
    tSSS by the authors. 60 Mandarin stories (story_N.wav, 16 kHz), one run per story (run N = story N), six
    visits (session = visit) of 10 runs in a fixed order; condition `story`, trial = run = story id, starting at the
    sound onset and as long as the wav.

    drift_correction: clock drift corrected by resampling (default +500 ppm), None to disable. Channels: MEG and
    BIO001 (misc). Stimuli: wav as shipped and a TextGrid (words, characters) from the authors' alignment.
    sub-06 runs 58-60 are skipped (copies of sub-05's). See notes.md.
    """

    def __init__(self, download_dir: str, drift_correction: float | None = DRIFT):
        self.download_dir = download_dir
        self.drift = drift_correction or 0.0
        ann = os.path.join(download_dir, "derivatives", "annotations")  # files misplaced upstream: find by name
        self.annotations = {os.path.basename(p): p for p in glob.glob(f"{ann}/**/story_*_time.mat", recursive=True)}

    def parse(self) -> Iterable[TrialRecord]:
        for sub_dir in sorted(glob.glob(os.path.join(self.download_dir, "sub-*"))):
            sub = os.path.basename(sub_dir)[4:]
            for session, stories in enumerate(VISITS, 1):
                for position, run in enumerate(stories, 1):
                    fif = os.path.join(sub_dir, "meg", f"sub-{sub}_task-RDR_run-{run}_meg.fif")
                    if (sub, run) in SKIP or not os.path.exists(fif):
                        continue
                    name = f"story_{run}"
                    wav = os.path.join(self.download_dir, "stimuli", "audio", f"{name}.wav")
                    interval = self._median_interval(run) if (sub, run) in NO_BEG else None
                    extra = dict(story=run, run=run, visit=session, position_in_visit=position,
                                 file=os.path.basename(fif))
                    yield TrialRecord(
                        subject=int(sub), session=session, trial=run, condition="story", ns_type="meg",
                        stimulus=[StimulusRecord("audio", name, _audio_loader(wav), True, "audio"),
                                  StimulusRecord("audio", name, self._textgrid_loader(run, wav), True, "textgrid")],
                        neural_data_fn=_meg_loader(fif, wav, self.drift, interval, extra))

    def _median_interval(self, run: int) -> float:
        """Median End - Beg (samples) of a run over the other subjects' events.tsv."""
        d = []
        for f in glob.glob(os.path.join(self.download_dir, "sub-*", "meg", f"sub-*_task-RDR_run-{run}_events.tsv")):
            sub = os.path.basename(f)[4:6]
            if (sub, run) in NO_BEG | SKIP:
                continue
            ev = pd.read_csv(f, sep="\t", encoding="utf-8-sig").set_index("value")["sample"]
            d.append(ev[END] - ev[BEG])
        if not d:
            raise ValueError(f"run {run}: no other subject to reconstruct the Beg trigger from")
        return float(np.median(d))

    def _textgrid_loader(self, story: int, wav: str):
        """Tiers words and characters, wav time; zero-length tokens dropped, identical intervals merged."""
        def _loader() -> str:
            fs, x = wavfile.read(wav, mmap=True)
            tg = textgrid.TextGrid(maxTime=len(x) / fs)
            for tier, level in (("words", "word"), ("characters", "char")):
                m = loadmat(self.annotations[f"story_{story}_{level}_time.mat"])
                start = np.round(m["start"][0] - FMRI_OFFSET_S, 3)
                end = np.round(m["end"][0] - FMRI_OFFSET_S, 3)
                t = textgrid.IntervalTier(tier, 0, len(x) / fs)
                prev = None
                for a, b, mark in zip(start, end, (str(w).strip() for w in m[level])):
                    if b <= a:
                        continue
                    if prev is not None and (prev.minTime, prev.maxTime) == (a, b):
                        prev.mark += mark  # several punctuation marks share one pause
                        continue
                    t.add(float(a), float(b), mark)
                    prev = t.intervals[-1]
                tg.append(t)
            f = _Buffer()
            tg.write(f)
            return f.getvalue()

        return _loader


def beg_end(raw: mne.io.BaseRaw) -> tuple[int | None, int]:
    """First Beg and the next End trigger (samples from the first stored sample); Beg None if missing."""
    ev = mne.find_events(raw, "STI101", shortest_event=1, consecutive=True, verbose="ERROR")
    samples, codes = ev[:, 0] - raw.first_samp, ev[:, 2]
    beg = samples[codes == BEG]
    beg = int(beg[0]) if beg.size else None
    end = samples[(codes == END) & (samples > (beg if beg is not None else -1))]
    if not end.size:
        raise ValueError(f"{raw.filenames[0]}: no End trigger")
    return beg, int(end[0])


def _meg_loader(fif: str, wav: str, drift: float, interval: float | None, extra: dict):
    def _loader():
        raw = mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")
        if raw.info["sfreq"] != 1000:
            raise ValueError(f"{fif}: sfreq {raw.info['sfreq']}")
        beg, end = beg_end(raw)
        note = NOTES
        if beg is None or interval is not None:
            if beg is not None or interval is None:
                raise ValueError(f"{fif}: Beg trigger {'present' if beg is not None else 'missing'} unexpectedly")
            beg = end - interval
            note += " Beg trigger missing (README): reconstructed as End - median End-Beg of the story."
        fs, x = wavfile.read(wav, mmap=True)
        n_out = math.ceil(len(x) * 1000 / fs)
        onset = beg + SOUND_DELAY_MS
        picks = mne.pick_types(raw.info, meg=True).tolist() + [raw.ch_names.index(c) for c in BIO]
        out = crop_on_audio_clock(raw, onset, n_out, drift, picks=picks, sfreq_out=1000)
        if out.n_times != n_out:
            raise ValueError(f"{fif}: recording ends {n_out - out.n_times} samples before the stimulus")
        out.set_channel_types({c: "misc" for c in BIO}, on_unit_change="ignore")
        si = raw.info["subject_info"] or {}
        mi = raw.info["proc_history"][0]["max_info"]
        with out.info._unlock():
            out.info["line_freq"] = 50.0
            out.info["subject_info"] = {"his_id": f"sub-{os.path.basename(fif)[4:6]}",
                                        **{k: si[k] for k in ("sex", "hand") if k in si}}
        out.info["description"] = provenance(
            "sw_trigger", "software (code run_story*.m: parallel-port TTL after PsychPortAudio Start; 39.5 ms "
            "sound delay measured with a sound sensor by the authors, paper)", note, drift_ppm=500, jitter_ms=1,
            drift_corrected_ppm=round(drift * 1e6, 3), **extra, beg_sample=round(float(beg), 1), end_sample=end,
            beg_reconstructed=interval is not None, sound_delay_ms=SOUND_DELAY_MS, onset_sample=round(onset, 1),
            sss=(f"tSSS by the authors ({raw.info['proc_history'][0]['creator']}; in/out order "
                 f"{mi['sss_info']['in_order']}/{mi['sss_info']['out_order']}, origin "
                 f"{np.round(mi['sss_info']['origin'] * 1000).astype(int).tolist()} mm head frame, buffer "
                 f"{mi['max_st']['buflen']:g} s, correlation {mi['max_st']['subspcorr']:.2f})"),
            sss_rank=int(mi["sss_info"]["nfree"]), bads=out.info["bads"], reference="none (MEG)",
            external_sensors=BIO, chpi="continuous HPI, 4 coils at 293, 307, 314, 321 Hz (meg.json)")
        return out

    return _loader


def _audio_loader(path: str):
    def _loader():
        fs, x = wavfile.read(path)
        return {"fs": fs, "data": x[None, :]}

    return _loader


class _Buffer(io.StringIO):
    """StringIO that survives TextGrid.write closing it."""

    def close(self):
        pass


ADAPTOR = Wang2022Adaptor
