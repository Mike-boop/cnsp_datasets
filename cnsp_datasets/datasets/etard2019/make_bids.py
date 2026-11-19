"""
Build an EEG-BIDS version of Etard et al. 2019 from the original record (Zenodo 7086209,
EtardBrainstemAndComprehension.zip): raw BrainVision recordings with the Sound stimtrack kept, one run per condition
part, stream onsets and presented SNR measured from the stimtrack, and all played streams as wav files.

    python -m cnsp_datasets.datasets.etard2019.make_bids <EtardBrainstemAndComprehension dir> <stimtrack.csv> <bids out>

<stimtrack.csv>: per run onsets, SNR and drift from the Sound channel (tmp/review/scripts/etard_stimtrack.py).
.eeg files are hard-linked, not copied (same file system as the source). Subjects keep the numbering of the HDF5
release (Zenodo 7778289, P00-P19), which follows the sorted original IDs (YH00 .. YH20 without YH05).
"""
from __future__ import annotations

import glob
import os
import shutil
import sys

import numpy as np
import pandas as pd
from scipy.io import loadmat, wavfile

from cnsp_datasets.bids import write as write_module
from cnsp_datasets.bids.write import channels_of, copy_brainvision, link, markers, write_json, write_tsv

FS = 44100
TASKS = {  # original condition -> (session, task)
    "clean": ("english", "clean"), "lb": ("english", "lb"), "mb": ("english", "mb"), "hb": ("english", "hb"),
    "fM": ("english", "fM"), "fW": ("english", "fW"),
    "cleanDutch": ("dutch", "clean"), "lbDutch": ("dutch", "lb"), "mbDutch": ("dutch", "mb"),
    "hbDutch": ("dutch", "hb"),
}
TASK_TEXT = {
    "clean": "Speech in quiet",
    "lb": "Speech in low-level babble noise (highest SNR of the three)",
    "mb": "Speech in medium-level babble noise",
    "hb": "Speech in high-level babble noise (lowest SNR)",
    "fM": "Attend a male speaker (story 'talesTroy', median F0 ~127 Hz) with a competing female speaker ('odin3')",
    "fW": "Attend a female speaker (story 'advOdy', median F0 ~200 Hz) with a competing male speaker ('greenForest')",
}


def streams(mat: str) -> dict:
    """Played streams of a condition part (44.1 kHz): speech, and babble / competing speaker / English sentences."""
    m = loadmat(mat)
    out = {"speech": (m["dutch"] if "dutch" in m else m["story"]).ravel()}
    if "babble" in m:
        out["babble"] = m["babble"].ravel()
    if "distractor" in m:
        out["competing"] = m["distractor"].ravel()
    if "english" in m:
        out["english"] = m["english"].ravel()
        out["sentences"] = list(zip(np.atleast_1d(m["idxBeginEn"].squeeze()), np.atleast_1d(m["idxEndEn"].squeeze())))
    return out


def main(src: str, stimtrack_csv: str, out: str) -> None:
    track = pd.read_csv(stimtrack_csv)
    # YH09 has a second header for cleanDutch run 4 (YH09_clean_4_dutch.vhdr, same data): keep the regular name
    track = (track.assign(alias=track.vhdr.str.endswith("_dutch.vhdr") & ~track.vhdr.str.contains("/Dutch/"))
             .sort_values("alias").drop_duplicates(["subject", "condition", "part"]).drop(columns="alias")
             .sort_values(["subject", "condition", "part"]))
    subjects = sorted(track.subject.unique())
    participants = []
    stim_written = set()
    for i, subject in enumerate(subjects):
        sub = f"{i:02d}"
        runs = track[track.subject == subject]
        for _, r in runs.iterrows():
            ses, task = TASKS[r.condition]
            stem = f"{out}/sub-{sub}/ses-{ses}/eeg/sub-{sub}_ses-{ses}_task-{task}_run-{r.part}"
            vhdr = os.path.join(src, r.vhdr)
            copy_brainvision(vhdr, f"{stem}_eeg")
            chans = channels_of(vhdr)
            write_tsv(f"{stem}_channels.tsv", pd.DataFrame(
                [dict(name=n, type="AUDIO" if n == "Sound" else "EEG", units=u, low_cutoff=0, high_cutoff=280,
                      status="good") for n, u in chans]))

            st = streams(os.path.join(src, r.stim_mat))
            stim_dir = f"{ses}/{task}"
            files = {k: f"{stim_dir}/run-{r.part}_{k}.wav" for k in ("speech", "babble", "competing", "english") if k in st}
            for k, rel in files.items():
                if rel not in stim_written:
                    os.makedirs(os.path.dirname(f"{out}/stimuli/{rel}"), exist_ok=True)
                    wavfile.write(f"{out}/stimuli/{rel}", FS, st[k].astype(np.float32))
                    stim_written.add(rel)
            onset = r.onset_sample / 1000 + (r.refine_ms / 1000 if pd.notna(r.refine_ms) else 0)
            common = dict(stimtrack_r=r.r_attended, drift_ppm=r.drift_ppm)
            rows = [dict(onset=round(onset, 5), duration=round(len(st["speech"]) / FS, 5), sample=int(r.onset_sample),
                         trial_type="speech", stim_file=files["speech"], snr_db=r.get("snr_db"), **common)]
            for k in ("babble", "competing"):
                if k in st:
                    off = int(r.unattended_offset_ms)
                    rows.append(dict(onset=round(onset + off / 1000, 5), duration=round(len(st[k]) / FS, 5),
                                     sample=int(r.onset_sample) + off, trial_type=k, stim_file=files[k],
                                     stimtrack_r=r.r_unattended))
            if "english" in st:
                rows.append(dict(onset=round(onset, 5), duration=round(len(st["english"]) / FS, 5),
                                 sample=int(r.onset_sample), trial_type="english_track", stim_file=files["english"]))
                for b, e in st["sentences"]:  # MATLAB 1-based, inclusive
                    rows.append(dict(onset=round(onset + (b - 1) / FS, 5), duration=round((e - b + 1) / FS, 5),
                                     sample=int(r.onset_sample) + int(round((b - 1) / FS * 1000)),
                                     trial_type="english_sentence"))
            for kind, desc, sample in markers(f"{stem}_eeg.vmrk"):
                if kind == "Stimulus":
                    rows.append(dict(onset=sample / 1000, duration=0, sample=sample, trial_type="trigger", value=desc))
            ev = pd.DataFrame(rows).sort_values(["onset", "trial_type"])
            cols = ["onset", "duration", "sample", "trial_type", "value", "stim_file", "snr_db", "stimtrack_r", "drift_ppm"]
            write_tsv(f"{stem}_events.tsv", ev.reindex(columns=cols))

            n_eeg = sum(n != "Sound" for n, _ in chans)
            write_json(f"{stem}_eeg.json", {
                "TaskName": task,
                "TaskDescription": ("Dutch audiobook (a language the participants did not speak) with short English "
                                    "sentences to detect; " if ses == "dutch" else "English audiobook; ")
                                   + TASK_TEXT[task].lower(),
                "SamplingFrequency": 1000, "PowerLineFrequency": 50, "SoftwareFilters": "n/a",
                "HardwareFilters": {"Anti-aliasing low-pass": {"cutoff (Hz)": 280}},
                "Manufacturer": "Brain Products", "ManufacturersModelName": "actiCHamp",
                "EEGChannelCount": n_eeg, "MiscChannelCount": len(chans) - n_eeg,
                "EEGReference": "Ear (BrainVision header: 'Reference Channel Name = Ear')", "EEGGround": "n/a",
                "EEGPlacementScheme": "10-10 (63 active electrodes, easycap-M1 names)", "CapManufacturer": "EasyCap",
                "RecordingType": "continuous",
                "SoundChannel": "Channel 'Sound' (type AUDIO) records the audio sent to the earphones (StimTrack); "
                                "stream onsets and SNR in *_events.tsv are measured from it.",
            })
        for f in glob.glob(f"{src}/eeg/{subject}/**/*.mat", recursive=True):
            link(f, f"{out}/sourcedata/sub-{sub}/beh/{os.path.basename(f)}")
        participants.append(dict(participant_id=f"sub-{sub}", original_id=subject, release_id=f"P{i:02d}",
                                 english_session="yes" if (runs.condition.map(lambda c: TASKS[c][0]) == "english").any() else "no",
                                 dutch_session="yes" if (runs.condition.map(lambda c: TASKS[c][0]) == "dutch").any() else "no",
                                 n_runs=len(runs)))
    write_tsv(f"{out}/participants.tsv", pd.DataFrame(participants))
    write_json(f"{out}/participants.json", {
        "original_id": {"Description": "Folder name in the original record (Zenodo 7086209, eeg/)"},
        "release_id": {"Description": "Participant ID in the HDF5 release (Zenodo 7778289)"},
        "english_session": {"Description": "Took part in the English session (ses-english)"},
        "dutch_session": {"Description": "Took part in the Dutch session (ses-dutch)"},
        "n_runs": {"Description": "Recorded runs (4 per condition)"},
    })
    write_json(f"{out}/events.json", {
        "onset": {"Description": "Stream onset measured from the Sound channel: cross-correlation of the attended "
                                 "speech (1 ms), refined by a Theil-Sen fit through 10 s windows (sub-ms); other "
                                 "streams at their measured offset from the speech", "Units": "s"},
        "duration": {"Description": "Stream duration (wav length)", "Units": "s"},
        "sample": {"Description": "0-based sample (1 kHz) of the event"},
        "trial_type": {"Levels": {
            "speech": "attended audiobook (English, or Dutch in ses-dutch)",
            "babble": "babble noise (lb/mb/hb): English runs 1 s before to 1 s after the speech; Dutch runs from 2 s "
                      "after the speech onset to its end",
            "competing": "competing speaker (fM/fW), from the speech onset",
            "english_track": "English sentences embedded in the Dutch audiobook's pauses (same length as the speech)",
            "english_sentence": "one English sentence (participants were asked to detect them)",
            "trigger": "software trigger written by the stimulus PC (value: marker code)"}},
        "value": {"Description": "BrainVision marker code of a trigger"},
        "stim_file": {"Description": "Audio played, relative to stimuli/ (44.1 kHz float32)"},
        "snr_db": {"Description": "Presented speech-to-noise ratio (babble or competing speaker) from least-squares "
                                  "gains of the Sound channel on the two streams, over the streams' full RMS",
                   "Units": "dB"},
        "stimtrack_r": {"Description": "Normalised peak cross-correlation of the Sound channel and the stream"},
        "drift_ppm": {"Description": "Clock drift of the EEG relative to the audio over the run (> 0: the EEG clock "
                                     "runs fast)", "Units": "ppm"},
    })
    # not included (in the earlier Zenodo versions): the original stimulus .mat files (same streams as stimuli/),
    # the set-aside recordings in eeg/<subject>/info/, the CND data and the CND conversion code
    os.makedirs(f"{out}/code", exist_ok=True)
    shutil.copy2(__file__, f"{out}/code/make_bids.py")
    shutil.copy2(write_module.__file__, f"{out}/code/bids_write.py")
    track.to_csv(f"{out}/sourcedata/stimtrack.csv", index=False)

    write_json(f"{out}/dataset_description.json", {
        "Name": "Etard et al. 2019: EEG to English and Dutch audiobooks in quiet, babble noise and with a competing "
                "speaker (BIDS, with stimtrack)",
        "BIDSVersion": "1.9.0", "DatasetType": "raw",
        "Authors": ["Octave Etard", "Tobias Reichenbach"],
        "License": "CC-BY-4.0 (TODO: confirm against the original record)",
        "ReferencesAndLinks": [
            "Etard O, Reichenbach T (2019). Neural speech tracking in the theta and in the delta frequency band "
            "differentially encode clarity and comprehension of speech in noise. J Neurosci 39(29):5750-5759.",
            "Original record: https://zenodo.org/records/7086209",
            "Convenience release (HDF5): https://zenodo.org/records/7778289"],
        "GeneratedBy": [{"Name": "cnsp_datasets make_bids.py", "Description": "code/make_bids.py"}],
        "SourceDatasets": [{"URL": "https://zenodo.org/records/7086209"}],
    })
    shutil.copy2(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bids_README.md"), f"{out}/README.md")
    print(f"wrote {out}: {len(participants)} participants, {len(track)} runs")


if __name__ == "__main__":
    main(*sys.argv[1:4])
