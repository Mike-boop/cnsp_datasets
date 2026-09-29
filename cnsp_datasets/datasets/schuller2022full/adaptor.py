from __future__ import annotations

import os, glob
import numpy as np

from scipy.io import wavfile
from scipy.signal import resample_poly, correlate, correlation_lags
from mne.io import read_raw_bti, BaseRaw

from typing import Iterable, Callable, Any, Dict
from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


EEG_CHANNELS = ['FP1','CPz','FC5','PO4','C4','P3','TP9','FP2',
                'P5','FC2','FT7','P4','F12','F3','P2','TP7',
                'CP1','F11','F5','C1','F4','PO5','C3','TP10',
                'CP6','Oz','F2','C6','FPz','FT10','FC1','PO6',
                'T8','Pz','FT9','F7','P1','FC6','FT8','CP5',
                'P8','C5','Fz','P6','T7','TP8','CP2','O1',
                'F1','C2','F8','PO3','Cz','P12','P7','O2',
                'F6','P11'
]


class Schueller2024MEGAdaptor:
    """
    Emits TrialRecord objects for the Schueller (2024) MEG dataset.

    Expected layout:
      <root>/subjects_dir/<participant Px>/raw/c,rfhp1.0Hz

    For each MEG run, we:
      - detect attended speaker (HP/LP) from the parent folder,
      - build 5 trials by slicing the Raw using audio segment durations,
      - attach attended+ignored stimuli per trial.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

        # discover MEG files
        pat = os.path.join(self.root, "**", "c,rfhp1.0Hz")
        self.raw_meg_files = sorted(glob.glob(pat, recursive=True))
        self.raw_meg_files = [f for f in self.raw_meg_files if "zweiter Versuch" not in f]
        if not self.raw_meg_files:
            raise FileNotFoundError(f"No MEG files found under {pat}")
        
        self.audio = self._load_audio_1024Hz()

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Emit one TrialRecord per (run x trial). Trials are 1..5.
        Subject id & trial index inferred from folder names/order.
        """
        for meg_fpath in self.raw_meg_files:

            path_parts = meg_fpath.split(os.sep)
            subject = path_parts[-3].split("_")[0]  # e.g., "P6", "P65_falschZugehört_Messung_neugestartet"
            subject = int(subject.replace("P", ""))  # convert to int

            if subject != 7:
                continue  # redo 7

            # let's extract the stimtrack channel
            raw = read_raw_bti(meg_fpath, convert=True, preload=False, verbose="ERROR")
            stimtrack = raw.copy().pick("EXT 004").resample(1024).get_data()[0]

            # now we can iterate over audio trials and ge the onsets using crosscorr method
            for i, each_key in enumerate(self.audio.keys()):

                audio_data = self.audio[each_key]["data_resampled"].mean(axis=0) # audio is mixed diotically
                t_ons = self.get_crosscorr_alignment(audio_data, stimtrack)/1024.0
                t_off = t_ons + len(audio_data)/1024.0

                meg_loader = self._make_meg_loader(meg_fpath, t_ons, t_off)
                attended_audio_loader = self._make_audio_loader(
                    self.audio[each_key]["file_attended"]
                )
                ignored_audio_loader = self._make_audio_loader(
                    self.audio[each_key]["file_ignored"]
                )


                stimuli = [
                    StimulusRecord("audio", self.audio[each_key]["attended_name"], attended_audio_loader, True,  feature_name="audio"),
                    StimulusRecord("audio", self.audio[each_key]["ignored_name"],  ignored_audio_loader,  False, feature_name="audio"),
                ]
            
                yield TrialRecord(
                    subject=subject,
                    session=1,
                    trial=i+1,
                    condition="competing",
                    ns_type="meg",
                    stimulus=stimuli,
                    neural_data_fn=meg_loader,
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # --------------------------- Audio helpers ---------------------------

    def _load_audio_1024Hz(self):
        """Preload all audio file paths into a dict for quick access."""
        audio_dir = os.path.join(self.root, "Audio")
        audio_dict = {}

        attend_files = sorted(glob.glob(os.path.join(audio_dir, "attended_speech", "*.wav")))
        for attended_file in attend_files:
            attended_audiobook = int(os.path.basename(attended_file).split("_")[0].replace("audiobook", ""))
            audiobook_part = int(os.path.basename(attended_file).split("_")[1].replace(".wav", ""))

            if attended_audiobook == 1:
                ignored_file = os.path.join(audio_dir, "ignored_speech", f"audiobook4_{audiobook_part}.wav")
                dict_key = f"attend-LP-{audiobook_part}"
                new_attended_name = f"LP1_{audiobook_part}"
                new_ignored_name = f"HP4_{audiobook_part}"
            elif attended_audiobook == 3:
                ignored_file = os.path.join(audio_dir, "ignored_speech", f"audiobook2_{audiobook_part}.wav")
                dict_key = f"attend-HP-{audiobook_part}"
                new_attended_name = f"HP3_{audiobook_part}"
                new_ignored_name = f"LP2_{audiobook_part}"

            fs, data_attended = wavfile.read(attended_file)
            _,  data_ignored  = wavfile.read(ignored_file)

            if np.ndim(data_attended) == 2:
                data_attended = data_attended.mean(axis=1)
            if np.ndim(data_ignored) == 2:
                data_ignored = data_ignored.mean(axis=1)

            data_attended = resample_poly(data_attended.squeeze().astype(float), up=1024, down=fs)
            data_ignored  = resample_poly(data_ignored.squeeze().astype(float),  up=1024, down=fs)
            audio_dict[dict_key] = {
                "data_resampled":np.array([data_attended, data_ignored]),
                "file_attended": attended_file,
                "file_ignored":  ignored_file,
                "attended_name": new_attended_name,
                "ignored_name":  new_ignored_name
            }

        return audio_dict
    
    def get_crosscorr_alignment(self, stim_audio: np.ndarray, stimtrack: np.ndarray) -> int:
        """Compute lag (in samples) to align stim_audio to stimtrack using cross-correlation."""

        # Cross-correlation
        corr = correlate(stimtrack, stim_audio, mode='full')
        lags = correlation_lags(len(stimtrack), len(stim_audio), mode='full')
        lag = lags[np.argmax(corr)]
        return lag

    def _make_audio_loader(self, wav_path: str) -> Callable[[], Dict[str, Any]]:
        def _loader() -> Dict[str, Any]:
            fs, audio = wavfile.read(wav_path)
            if audio.ndim == 2:
                audio = audio.mean(axis=1)
            return {"fs": int(fs), "data": audio[None, :]}
        return _loader

    # --------------------------- MEG helpers ---------------------------

    def _make_meg_loader(self, meg_path: str, t0: float, t1: float) -> Callable[[], BaseRaw]:
        """Lazy: read FIF (preload=False) and crop to [t0, t1]."""
        def _loader() -> BaseRaw:
            raw = read_raw_bti(meg_path, preload=False, verbose="ERROR", convert=True)

            # rename MEG channels
            raw.rename_channels(lambda x: x.replace("MEG ", "A"))  # BTi sometimes has trailing spaces

            # rename EEG channels and set channel types
            raw.rename_channels(lambda x: x.replace("-1", ""))  # remove trailing -1 from EEG channels
            raw.set_channel_types({ch: "eeg" for ch in EEG_CHANNELS if ch in raw.ch_names})

            # rename EOG channel
            raw.rename_channels({"EEG 003": "EOG"})

            raw.pick(
                [f"A{i:03d}" for i in range(1, 249)] + \
                [ch for ch in EEG_CHANNELS if ch in raw.ch_names] + \
                ["EOG"]
            )

            tmax = raw.times[-1]
            if t0 >= tmax:
                print(f"Warning: requested t0={t0} exceeds data length {tmax}s in {meg_path}")
            return raw.copy().crop(tmin=t0, tmax=min(t1, tmax))
        return _loader


ADAPTOR = Schueller2024MEGAdaptor