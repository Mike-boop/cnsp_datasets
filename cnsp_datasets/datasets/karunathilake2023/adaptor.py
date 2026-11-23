from __future__ import annotations

import glob
import os
from typing import Callable, Iterable

import mne
import openpyxl

from cnsp_datasets.datasets.simon_base.common import (audio_loader, check_unique_subjects, crop_meg, find_one,
                                                      read_raw, rms_bads, stim_events, subject_number, wav_samples)
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1000
AUDIO_FS = 44100
N_PASSAGES = 36
# Trigger codes (exp.py); in the control study 166 is the second vocoded presentation (PRE2).
CONDITIONS = {"main": {164: "pre", 165: "clean", 166: "post"},
              "control": {164: "control-pre1", 166: "control-pre2", 165: "control-clean"}}
RATING_COLUMN = {"main": {164: "PRE", 166: "POST"}, "control": {164: "PRE1", 166: "PRE2"}}
FLAT_RATIO = 20  # channel rms below median / 20 in 10 x 10 s windows -> bad (notes.md section 5)
TRIGGER_TYPE = ("software (inferred: Presentation sends the TTL codes, paper; recorded on MISC 005-007; latency to "
                "sound onset and tube delay unknown, no audio channel)")
NOTES = ("Onset = trigger (one TTL code per passage onset, no offset codes), no shift and no drift correction (no "
         "audio channel and no offset triggers: drift not measurable; < 1 ms over a 26 s trial for typical clocks). "
         "Trial length = played wav. Units T. MEG 001-157 axial gradiometers (MNE type mag) + 3 reference "
         "magnetometers; MISC lines (TTL trigger lines, idle or noise-only ports) and STI 014 dropped. Flat channels "
         "in info['bads']. POST/PRE2 replays the same vocoded file as PRE.")
# Subject lists in the authors' exp.py: ALL = analysed pool (25 main + 11 control), good_sub2 = paper's 23 main.
AUTHORS_ALL = {
    "R2684", "R2808", "R2813", "R2702", "R2821", "R2822", "R2823", "R2824", "R2826", "R2827", "R2831", "R2698",
    "R2851", "R2854", "R2859", "R2865", "R2866", "R2877", "R2876", "R2881", "R2882", "R2883", "R2885", "R2886",
    "R2891", "R2963", "R2964", "R2967", "R2969", "R2970", "R2981", "R2982", "R2983", "R2984", "R2994", "R3009"}
AUTHORS_MAIN_ANALYSED = {
    "R2684", "R2808", "R2702", "R2821", "R2822", "R2823", "R2824", "R2826", "R2827", "R2831", "R2698", "R2851",
    "R2854", "R2859", "R2865", "R2866", "R2877", "R2876", "R2881", "R2882", "R2883", "R2885", "R2886"}


class Karunathilake2023Adaptor:
    """
    Clear vs noise-vocoded audiobook passages (Karunathilake, Kulasingham & Simon 2023, PNAS; Dryad
    doi:10.5061/dryad.sbcc2frd6): KIT 157-channel MEG at 1 kHz, one recording per participant. Main study (27
    shipped): 36 passages, each as PRE (vocoded), CLEAN, POST (same vocoded file). Control study (12): PRE1, PRE2
    (both vocoded), CLEAN. Trials 1-108 in presentation order; the k-th trigger of a code is passage k (story
    order, exp.py). Subject = R-number mod 1000 (R-number in the sidecar). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(find_one(os.path.join(self.root, "**/split1.wav")))
        ratings = {study: _ratings(find_one(os.path.join(self.root, f"**/Ratings_{study}.xlsx")))
                   for study in CONDITIONS}
        paths = sorted(glob.glob(os.path.join(self.root, "**", "meg_*", "R*", "R*_voc-raw.fif"), recursive=True))
        pids = [os.path.basename(p).split("_")[0] for p in paths]
        check_unique_subjects(pids)
        for path, pid in zip(paths, pids):
            study = "control" if os.sep + "meg_control" + os.sep in path else "main"  # meg_main1, meg_main2
            raw = read_raw(path, FS)
            events = stim_events(raw, CONDITIONS[study])
            if len(events) != 3 * N_PASSAGES:
                raise ValueError(f"{path}: {len(events)} stimulus triggers, expected {3 * N_PASSAGES}")
            count = dict.fromkeys(CONDITIONS[study], 0)
            for trial, (sample, code) in enumerate(events[:, [0, 2]].tolist(), 1):
                count[code] += 1
                passage = count[code]
                name = f"split{passage}" + ("" if code == 165 else "_vocoded")
                onset = sample - raw.first_samp
                column = RATING_COLUMN[study].get(code)
                rating = ratings[study][pid][passage]
                description = provenance(
                    "sw_trigger", TRIGGER_TYPE, NOTES, participant=pid, study=study, passage=passage,
                    presentation=CONDITIONS[study][code], trigger_code=code, onset_s=onset / FS,
                    stimulus_file=f"{name}.wav", vocoded=code != 165,
                    clarity_rating=rating[column] if column else None,
                    q2_as_shipped=rating["Q2"],
                    in_authors_pool=pid in AUTHORS_ALL,
                    in_authors_main_analysis=pid in AUTHORS_MAIN_ANALYSED if study == "main" else None)
                wav = os.path.join(stim_dir, f"{name}.wav")
                yield TrialRecord(
                    subject=subject_number(pid), session=1, trial=trial, condition=CONDITIONS[study][code],
                    ns_type="meg",
                    stimulus=[StimulusRecord("audio", name, audio_loader(wav, AUDIO_FS), is_attended=True)],
                    neural_data_fn=_meg_loader(path, onset, wav_samples(wav, AUDIO_FS, FS), description),
                )


def _ratings(path: str) -> dict:
    """{participant: {passage: {column: value}}} from the per-participant sheets (columns Trial, PRE/PRE1, Q2, ...)."""
    out = {}
    for ws in openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets:
        rows = [r for r in ws.iter_rows(values_only=True) if r and r[0] is not None]
        out[ws.title] = {int(r[0]): {h: r[i] for i, h in enumerate(rows[0]) if i > 0 and h} for r in rows[1:]}
    return out


def _meg_loader(path: str, onset: int, n_out: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    """Trial from the onset trigger (opening R####_voc-raw.fif joins the -1 split); flat gradiometers as bads."""
    def _loader():
        return crop_meg(read_raw(path, FS), onset, n_out, description, rms_bads(path, FS, FLAT_RATIO))

    return _loader


ADAPTOR = Karunathilake2023Adaptor
