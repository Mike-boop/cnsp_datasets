"""
Build an EEG-BIDS version of Weissbart et al. 2019 from the original record (Zenodo 7086168, WeissbartSurprisal.zip):
raw BrainVision recordings with the Sound stimtrack kept, story onsets measured from the stimtrack, the stimuli with
their alignments and word-level features, and the authors' preprocessing files and CND data as derivatives.

    python -m cnsp_datasets.datasets.weissbart2019.make_bids <WeissbartSurprisal dir> <stimtrack.csv> <bids out dir>

<stimtrack.csv>: per participant x story onset and drift from the Sound channel (tmp/review/scripts/
weissbart_stimtrack.py). Large files (.eeg, CND .mat) are hard-linked, not copied, so the source and the output must be
on the same file system; delete the source only after the upload. Subjects keep the numbering of the convenience
release (Zenodo 7775260, P00-P12), which follows the sorted original folders (P01 .. P14 without P11).
"""
from __future__ import annotations

import glob
import os
import shutil
import sys

import numpy as np
import pandas as pd
from scipy.io import wavfile

from cnsp_datasets.bids import write as write_module
from cnsp_datasets.bids.write import channels_of, copy_brainvision, link, write_json, write_tsv

STORIES = [f"AUNP0{i}" for i in range(1, 9)] + [f"BROP0{i}" for i in range(1, 4)] + [f"FLOP0{i}" for i in range(1, 5)]
TASK = "audiobook"
NOT_PLAYED = {("P04", "BROP01")}  # original folder ID, story: absent from the stimtrack (see README)


def main(src: str, stimtrack_csv: str, out: str) -> None:
    folders = sorted(d for d in glob.glob(f"{src}/eeg/*") if os.path.isdir(d))
    track = pd.read_csv(stimtrack_csv)
    participants = []
    for i, folder in enumerate(folders):
        orig = os.path.basename(folder).split("_")[0]
        sub = f"{i:02d}"
        vhdr = glob.glob(f"{folder}/*.vhdr")[0]
        stem = f"{out}/sub-{sub}/eeg/sub-{sub}_task-{TASK}_eeg"
        copy_brainvision(vhdr, stem)

        bads = open(f"{folder}/bad_channels.txt").read().split() if os.path.exists(f"{folder}/bad_channels.txt") else []
        chans = channels_of(vhdr)
        write_tsv(f"{stem[:-4]}_channels.tsv", pd.DataFrame(
            [dict(name=n, type="AUDIO" if n == "Sound" else "EEG", units=u, low_cutoff=0, high_cutoff=280,
                  status="bad" if n in bads else "good",
                  status_description="marked bad by the authors (bad_channels.txt)" if n in bads else "n/a")
             for n, u in chans]))

        t = track[track.participant == orig].set_index("story")
        rows = []
        for story in STORIES:
            if (orig, story) in NOT_PLAYED:
                continue
            r = t.loc[story]
            sample = int(round(r.onset_sound_s * 1000))
            fs, audio = wavfile.read(f"{src}/stim/alignment_data/{story}/{story}.wav")
            rows.append(dict(onset=round(sample / 1000 + r.refine_ms / 1000, 5), duration=round(len(audio) / fs, 5),
                             sample=sample, trial_type="story", stim_file=f"{story}/{story}.wav",
                             onset_listed=r.onset_mat_s, stimtrack_r=r.r, stimtrack_windows=int(r.n_windows),
                             drift_ppm=round(r.drift_ppm, 2)))
        ev = pd.DataFrame(rows).sort_values("onset")
        ev.insert(4, "trial", np.arange(1, len(ev) + 1))
        write_tsv(f"{stem[:-4]}_events.tsv", ev)

        n_eeg = sum(n != "Sound" for n, _ in chans)
        write_json(f"{stem}.json", {
            "TaskName": TASK,
            "TaskDescription": "Passive listening to 15 chapters of English audiobooks (about 2.5 min each), "
                               "with comprehension questions after each chapter.",
            "SamplingFrequency": 1000, "PowerLineFrequency": 50, "SoftwareFilters": "n/a",
            "HardwareFilters": {"Anti-aliasing low-pass": {"cutoff (Hz)": 280}},
            "Manufacturer": "Brain Products", "ManufacturersModelName": "actiCHamp",
            "EEGChannelCount": n_eeg, "MiscChannelCount": len(chans) - n_eeg,
            "EEGReference": "Ear (BrainVision header: 'Reference Channel Name = Ear')", "EEGGround": "n/a",
            "EEGPlacementScheme": "10-10 (63 active electrodes, easycap-M1 names)", "CapManufacturer": "EasyCap",
            "RecordingType": "continuous",
            "SoundChannel": "Channel 'Sound' (type AUDIO) records the audio sent to the earphones (StimTrack); "
                            "story onsets in *_events.tsv are measured from it.",
        })

        # authors' preprocessing files and the behavioural (psychtoolbox) file
        for f in glob.glob(f"{folder}/*"):
            b = os.path.basename(f)
            if b.endswith((".vhdr", ".vmrk", ".eeg")):
                continue
            if b.endswith(".mat"):
                link(f, f"{out}/sourcedata/sub-{sub}/beh/{b}")
            else:
                link(f, f"{out}/derivatives/authors_preprocessing/sub-{sub}/{b}")
        participants.append(dict(participant_id=f"sub-{sub}", original_id=orig, release_id=f"P{i:02d}",
                                 cnd_id=f"S{i + 1:02d}", n_stories=len(ev)))
    write_tsv(f"{out}/participants.tsv", pd.DataFrame(participants))
    write_json(f"{out}/participants.json", {
        "original_id": {"Description": "Folder name in the original record (Zenodo 7086168, eeg/)"},
        "release_id": {"Description": "Participant ID in the HDF5 release (Zenodo 7775260)"},
        "cnd_id": {"Description": "Subject file in the CND derivative (derivatives/CND/S<k>.mat; toCND.m numbers the sorted eeg/ folders)"},
        "n_stories": {"Description": "Stories with valid EEG (see README for the one missing story)"},
    })
    write_json(f"{out}/task-{TASK}_events.json", {
        "onset": {"Description": "Story onset measured from the Sound channel: cross-correlation (1 ms), refined by "
                                 "a Theil-Sen fit through 10 s windows (sub-ms)", "Units": "s"},
        "duration": {"Description": "Story duration (wav length)", "Units": "s"},
        "sample": {"Description": "Sample (0-based) of the story onset at 1 kHz; the convenience release cut the EEG "
                                  "here"},
        "trial_type": {"Description": "story: one audiobook chapter"},
        "trial": {"Description": "Presentation order within the session"},
        "stim_file": {"Description": "Audio played, relative to stimuli/"},
        "onset_listed": {"Description": "Onset from the authors' stim/onsets.mat (original record)", "Units": "s"},
        "stimtrack_r": {"Description": "Normalised peak cross-correlation of the Sound channel and the story's first "
                                       "60 s (a transient on the Sound channel can make it small)"},
        "stimtrack_windows": {"Description": "10 s windows (every 5 s) whose lag fit has r >= 0.1; the onset "
                                             "refinement and drift come from these"},
        "drift_ppm": {"Description": "Clock drift of the EEG relative to the audio over the story (Theil-Sen slope "
                                     "of the lags; > 0: the EEG clock runs fast)", "Units": "ppm"},
    })

    # stimuli: audio, alignments, transcripts, word-level features
    for story in STORIES:
        for f in glob.glob(f"{src}/stim/alignment_data/{story}/*"):
            link(f, f"{out}/stimuli/{story}/{os.path.basename(f)}")
        for kind in ("word_frequencies", "surprisal", "transcripts"):
            for f in glob.glob(f"{src}/stim/{kind}/{story}*"):
                link(f, f"{out}/stimuli/{story}/{kind}/{os.path.basename(f)}")
    link(f"{src}/stim/onsets.mat", f"{out}/sourcedata/onsets.mat")

    # derivatives: CND files, stimtrack table
    for f in glob.glob(f"{src}/dataCND/*.mat"):
        link(f, f"{out}/derivatives/CND/{os.path.basename(f)}")
    deriv = {"Name": "Weissbart 2019 derivatives", "BIDSVersion": "1.9.0", "DatasetType": "derivative"}
    write_json(f"{out}/derivatives/CND/dataset_description.json",
               dict(deriv, Name="Preprocessed data in the Continuous-event Neural Data (CND) format",
                    GeneratedBy=[{"Name": "toCND.m (code/)", "Description": "authors' CNSP conversion"}]))
    write_json(f"{out}/derivatives/authors_preprocessing/dataset_description.json",
               dict(deriv, Name="Authors' preprocessing files (bad channels, ICA, event files)",
                    GeneratedBy=[{"Name": "MNE-Python (authors)"}]))

    # code
    for f in [f"{src}/toCND.m"] + glob.glob(f"{src}/preproc_functions/*"):
        link(f, f"{out}/code/{os.path.relpath(f, src)}")
    shutil.copy2(__file__, f"{out}/code/make_bids.py")
    shutil.copy2(write_module.__file__, f"{out}/code/bids_write.py")

    write_json(f"{out}/dataset_description.json", {
        "Name": "Weissbart et al. 2019: EEG to continuous English audiobooks (BIDS, with stimtrack)",
        "BIDSVersion": "1.9.0", "DatasetType": "raw",
        "Authors": ["Hugo Weissbart", "Katerina D. Kandylaki", "Tobias Reichenbach"],
        "License": "CC-BY-4.0 (TODO: confirm against the original record)",
        "ReferencesAndLinks": [
            "Weissbart H, Kandylaki KD, Reichenbach T (2020). Cortical tracking of surprisal during continuous "
            "speech comprehension. J Cogn Neurosci 32(1):155-166. doi:10.1162/jocn_a_01467",
            "Original record: https://zenodo.org/records/7086168",
            "Convenience release (HDF5): https://zenodo.org/records/7775260"],
        "GeneratedBy": [{"Name": "cnsp_datasets make_bids.py", "Description": "code/make_bids.py"}],
        "SourceDatasets": [{"URL": "https://zenodo.org/records/7086168"}],
    })
    readme = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bids_README.md")).read()
    open(f"{out}/README.md", "w").write(readme)
    print(f"wrote {out}: {len(participants)} participants")


if __name__ == "__main__":
    main(*sys.argv[1:4])
