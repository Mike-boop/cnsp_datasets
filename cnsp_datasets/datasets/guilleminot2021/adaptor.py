from __future__ import annotations

import os
import glob
from typing import Iterable, Dict, List, Callable, Any

import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import resample_poly, correlate, correlation_lags

from mne.io import read_raw_brainvision, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


EEG_FNAME_DICT = {
    "al": {
        "1": "al.vhdr",
        "1_2": None,
        "2": "al_2.vhdr",
        "2_2": None
    },
    "yr": {
        "1": "yr.vhdr",
        "1_2": "yr2.vhdr",
        "2": "yr_2.vhdr",
        "2_2": None
    },
    "alio": {
        "1": "alio_1.vhdr",
        "1_2": None,
        "2": "alio_2.vhdr",
        "2_2": None
    },
    "chap": {
        "1": "chap_1.vhdr",
        "1_2": None,
        "2": "chap_2.vhdr",
        "2_2": None
    },
    "sep": {
        "1": "sep_1.vhdr",
        "1_2": None,
        "2": "sep_2.vhdr",
        "2_2": None
    },
    "phil": {
        "1": "phil_1.vhdr",
        "1_2": None,
        "2": "phil_2.vhdr",
        "2_2": None
    },
    "lad": {
        "1": "lad_1.vhdr",
        "1_2": "lad_1_1.vhdr",
        "2": "lad_2.vhdr",
        "2_2": None
    },
    "calco": {
        "1": "calco_1.vhdr",
        "1_2": None,
        "2": "calco_2.vhdr",
        "2_2": None
    },
    "hudi": {
        "1": "hudi_1.vhdr",
        "1_2": None,
        "2": "hudi_2.vhdr",
        "2_2": None
    },
    "nima": {
        "1": "nima.vhdr",
        "1_2": None,
        "2": "nima_2.vhdr",
        "2_2": None
    },
    "ogre": {
        "1": "ogre_1.vhdr",
        "1_2": None,
        "2": "ogre_2.vhdr",
        "2_2": None
    },
    "raqu": {
        "1": "raqu.vhdr",
        "1_2": None,
        "2": "raqu_2.vhdr",
        "2_2": None
    },
    "nikf": {
        "1": "nikf.vhdr",
        "1_2": None,
        "2": "nikf_2.vhdr",
        "2_2": None
    },
    "zartan": {
        "1": "zartan_1.vhdr",
        "1_2": None,
        "2": "zartan_2.vhdr",
        "2_2": None
    },
    "naga": {
        "1": "naga_1.vhdr",
        "1_2": None,
        "2": "naga_2.vhdr",
        "2_2": None
    },
    "miya": {
        "1": "miya_1.vhdr",
        "1_2": None,
        "2": "miya_2.vhdr",
        "2_2": None
    },
    "elios": {
        "1": "elios_1.vhdr",
        "1_2": "elios_1_2.vhdr",
        "2": "elios_2.vhdr",
        "2_2": None
    },
    "olio": {
        "1": "olio_1.vhdr",
        "1_2": None,
        "2": "olio_2.vhdr",
        "2_2": None
    }
}

PARTICIPANTS = [
    'al', 'yr', 'alio', 'chap', 'sep',
    'phil', 'lad', 'calco', 'hudi', 'nima',
    'ogre', 'raqu', 'nikf', 'zartan', 'naga',
    'miya', 'elios', 'olio'
]
SESSIONS = [1, 2]

# some trials are missing due to recording problems
MISSING_TRIALS = {'yr' : {1: [12]}, 'naga' : {1: [0,13,14,15], 2: [8]}, 'elios' : {1: [14]}}

# stable int id per participant (TrialRecord.subject requires int)
_SUB_INDEX = {p: i + 1 for i, p in enumerate(PARTICIPANTS)}


class Guilleminot2021Adaptor:
    """
    Adaptor for the Guilleminot 2021 dataset (EEG + audio alignment via Sound channel).

    Folder layout expected:
      <root>/
        ├─ Stimuli/Odin_<File>.wav
        └─ <participant>/<participant>_EEG_<session>/
             ├─ *.vhdr (unfortunately no standardised naming scheme)
             └─ <participant>_EEG_<session>.csv  (with columns: File, Type, Delay)

    Notes
    -----
    - We align each EEG trial window to the audio using X-corr of the "Sound" channel vs
      the audio resampled to 1 kHz
    - There was no sound in the tactile-only conditions. However, the vmrk files contain 
        precise triggering information (TDT trigger system) for the tactile stimulus onset.
        For some reason (TDT latency?), the TDT triggers lag the audio onset by 1.002 seconds
        (audio-tactile trials, x-corr method vs TDT trigger)
    - Condition:
        'audio-tactile' → 'audio-tactile-<Delay>' where '-' in Delay is replaced with 'm'
        otherwise the raw 'Type' (e.g., 'audio', 'tactile').
    - Missing trials can be skipped via a dict mapping 'participant' -> [trial_idx,...].
    - Subject IDs in TrialRecord are 1-based indices by participant order (stable mapping).
    """

    def __init__(
        self,
        download_dir: str,
    ):
        self.root = download_dir

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Emit a TrialRecord per (participant, session, trial).
        """
        for p in PARTICIPANTS:
            for ses in SESSIONS:
                eeg_dir = os.path.join(self.root, p, f"{p}_EEG_{ses}")
                if not os.path.isdir(eeg_dir):
                    continue

                eeg_files = (EEG_FNAME_DICT[p][str(ses)], EEG_FNAME_DICT[p][str(ses) + "_2"])
                vhdr_paths = [os.path.join(eeg_dir, vhdr) for vhdr in (eeg_files) if vhdr is not None]

                csv_path = os.path.join(eeg_dir, f"{p}_EEG_{ses}.csv")
                if not os.path.exists(csv_path):
                    continue

                info_df = pd.read_csv(csv_path)
                for trial_idx in info_df.index:

                    print(p, trial_idx)
                    if p in MISSING_TRIALS and ses in MISSING_TRIALS[p] and trial_idx in MISSING_TRIALS[p][ses]:
                        print("Skipping", trial_idx)
                        continue

                    file_token = str(info_df.loc[trial_idx, "File"])
                    wav_path = os.path.join(self.root, "Stimuli", f"Odin_{file_token}.wav")

                    stim_type = str(info_df.loc[trial_idx, "Type"])
                    if stim_type == "audio-tactile":
                        delay_str = str(info_df.loc[trial_idx, "Delay"])
                        delay_str = delay_str.replace('-', 'm')
                        condition = f"AT_{delay_str}"
                    elif stim_type == "audio":
                        condition = "A"
                    elif stim_type == "tactile":
                        condition = "T"

                    if info_df.loc[trial_idx, "Correlated"] == 0:
                        condition = "AT_mismatched"

                    # Build stimuli
                    all_stim = []

                    if "audio" in stim_type:
                        # raw audio stimulus
                        stim_name = f"Odin_{file_token}"
                        stim_audio = StimulusRecord(
                            modality="audio",
                            name=stim_name,
                            data_fn=self._make_audio_loader(wav_path),
                            is_attended=True,
                            feature_name="audio",
                        )
                        all_stim.append(stim_audio)

                        # and textgrid
                        tg_path = wav_path.replace(".wav", ".TextGrid")
                        stim_tg = StimulusRecord(
                            modality="audio",
                            name=stim_name,
                            data_fn=self._make_tg_loader(tg_path),
                            is_attended=True,
                            feature_name="textgrid",
                        )
                        all_stim.append(stim_tg)

                    if stim_type in ["audio-tactile", "tactile"] and condition != "AT_mismatched":
                        stim_name = f"Odin_{file_token}_delay_{delay_str}"
                        delay_int = info_df.loc[trial_idx, "Delay"]
                        stim = StimulusRecord(
                            modality="tactile",
                            name=stim_name,
                            data_fn=self._make_audio_loader(wav_path, delay=delay_int), # delay applied to tactile stim [ms]
                            is_attended=True,
                            feature_name="audio",
                        )
                        all_stim.append(stim)

                    if condition == "AT_mismatched":
                        pass # still need to figure out how to get the incongruent tactile stimuli

                    # Lazy EEG loader (align/crop via cross-correlation or annotation)

                    if p == "naga" and ses == 1: # hacky fix: first trial is missing from this eeg recording, so adjust the annotation that we are looking for.
                        eeg_annot_idx = trial_idx - 1
                    elif p == "naga" and ses == 2 and trial_idx > 8: # this session is missing an annotation altogether
                        eeg_annot_idx = trial_idx - 1
                    else:
                        eeg_annot_idx = trial_idx

                    neural_fn = self._make_eeg_loader(vhdr_paths, wav_path, stim_type, eeg_annot_idx)

                    yield TrialRecord(
                        subject=_SUB_INDEX[p],
                        session=ses,
                        trial=int(trial_idx),
                        condition=condition,
                        ns_type="eeg",
                        stimulus=all_stim,
                        neural_data_fn=neural_fn,
                        structural_data_fn=None,
                        behavioural_data_fn=None,
                    )

    # ------------------------ Lazy loaders ------------------------

    def _make_audio_loader(self, wav_path: str, delay: int = 0) -> Callable[[], Dict[str, Any]]:
        def _loader() -> Dict[str, Any]:
            fs, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]  # mono

            d = -int(delay * fs / 1000) # delay is audio onset wrt tactile, so invert here
            x = np.roll(x, d)
            print(d, delay)
            # if delay >= 0:
            #     x[:d] = 0 
            # else:
            #     x[d:] = 0
            return {"fs": int(fs), "waveform": np.asarray(x, dtype=float)[None, :]}
        return _loader
    
    def _make_tg_loader(self, tg_path: str) -> Callable[[], str]:
        def _loader() -> str:
            with open(tg_path, "r") as f:
                text = f.read()
            return text
        return _loader

    def _make_eeg_loader(self, vhdr_paths: List[str], wav_path: str, stim_type: str, eeg_annot_idx: int) -> Callable[[], BaseRaw]:
        """
        Loads EEG run, computes onset by x-corr Sound vs audio@1kHz, crops Raw to [onset, offset].
        """
        def _loader() -> BaseRaw:
            # audio @ 1 kHz
            fs_aud, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]
            audio_1k = resample_poly(x.astype(float), 1000, fs_aud)

            # EEG: read 'Sound' channel and filter as in your script
            raw = read_raw_brainvision(vhdr_paths[0], preload=False, verbose="ERROR")
            if len(vhdr_paths) > 1:
                raw2 = read_raw_brainvision(vhdr_paths[1], preload=False, verbose="ERROR")
                raw.append(raw2)

            annotations = [x for x in raw.annotations if x["description"] == 'Response/R  3']
            onset = annotations[eeg_annot_idx]["onset"] + 1.002

            # # I'm pretty sure we can just use the TDT triggers
            # # but in case we get dodgy results, here's the x-corr method
            # # in this case one should be aware that in T-only stimulation 
            # # there is no stimtrack, so the x-corr method doesn't work at all
            # raw_st = raw.copy().pick(["Sound"]).load_data()
            # raw_st.filter(1.0, None, picks="Sound", verbose="ERROR")
            # stim = raw_st.get_data().ravel()

            # # x-corr (assume Sound is at 1 kHz; if not, consider resampling stim)
            # crosscorr = correlate(stim, audio_1k, mode="same")
            # lags = correlation_lags(len(stim), len(audio_1k), mode="same")
            # lag = int(lags[np.argmax(crosscorr)])
            # onset = lag / 1000.0
            
            duration = len(audio_1k) / 1000.0
            tmin, tmax = onset, onset + duration

            return raw.copy().crop(tmin=tmin, tmax=tmax)
        return _loader

    # ------------------------ Discovery helpers ------------------------

    def _discover_participants(self) -> List[str]:
        # participant directories at root level
        candidates = [
            os.path.basename(p)
            for p in glob.glob(os.path.join(self.root, "*"))
            if os.path.isdir(p) and os.path.exists(os.path.join(p, f"{os.path.basename(p)}_EEG_1"))
        ]
        return sorted(candidates)


ADAPTOR = Guilleminot2021Adaptor