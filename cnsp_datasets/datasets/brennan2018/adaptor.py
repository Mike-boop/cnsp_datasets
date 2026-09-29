from __future__ import annotations

import os
import glob
import mne
import numpy as np
import pandas as pd
from typing import Iterable, Callable, Any, Dict, List

from mne.io import RawArray, BaseRaw
from mne.filter import filter_data
from mne.channels import make_standard_montage

from scipy.io import wavfile
from scipy.signal import (
    hilbert, resample_poly, correlate, correlation_lags
)
from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.datasets.utils import multi_tier_dict_to_textgrid


mne.set_log_level("CRITICAL")


class Brennan2018Adaptor:
    """
    Emits TrialRecord objects for the Brennan & Hale 2018 (v2) dataset.

    Expected layout:
      - Raw EEG: <download_dir>/S*.vhdr
      - Audio:   <download_dir>/audio/DownTheRabbitHoleFinal_SoundFile{1..12}.wav

    Two methods for computing trial onsets:
      1) Use cross-correlation of AUX/AUD stim channel with the speech envelope (500 Hz), unless
         the subject is known to lack/contain unusable stim channel.
      2) Use triggers provided in the raw data headers (.vhdr files)
    """

    SESSION = 1  # only one session in this dataset
    FS_EEG = 500
    NOISY_OR_NO_STIMTRACK = [9, 16, 22, 23, 39] + [5, 38] # 5,38 have no stimtrack; others have noisy stimtrack. Perhaps adaptor was not plugged into amplifier?

    def __init__(self, download_dir: str, alignment_method: List[str] = ["annot", "crosscorr"]):
        """
        Parameters
        ----------
        download_dir : str
            Path where the raw dataset is downloaded.
        alignment_method : list of str
            Preferred methods for determining story part onsets.
            Options are "annot" (use .vhdr triggers) and "crosscorr" (use stimtrack channel).
            The list order indicates the order of preference for the two possible alignment methods. 
        """
        self.download_dir = download_dir
        self.alignment_method = alignment_method

        self.stim_info = self._get_audiobook_envelopes_and_durations()

    # --------------------------- Public API ----------------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yield TrialRecord for each subject x story part (1..12).
        """
        for vhdr_path in self._discover_raw_recordings():
            print(vhdr_path)
            sub = os.path.splitext(os.path.basename(vhdr_path))[0]  # e.g., "S07"
            sub_idx = int(sub.replace("S", ""))
            raw = mne.io.read_raw_brainvision(vhdr_path, preload=False, verbose="ERROR")
            assert raw.info["sfreq"] == self.FS_EEG, f"Expected {self.FS_EEG} Hz EEG, got {raw.info['sfreq']} Hz for {sub}"

            for segment in range(1, 13):

                # first, get the onset of the segment. Use the most preferred alignment method first.
                onset = None
                for method in self.alignment_method:
                    onset = self._get_onset(raw, sub_idx, segment, method)
                    if onset is not None:
                        break
                if onset is None:
                    raise RuntimeError(f"Could not determine onset for {sub} segment {segment} using alignment methods {self.alignment_method}")
                
                # let's refine the raw object:
                raw.drop_channels([ch for ch in raw.ch_names if ch in ["Aux5", "AUD"]])
                ch_types_mapping = {ch: "eeg" for ch in raw.ch_names if ch.isnumeric()}
                ch_types_mapping.update({"VEOG":"eog"})
                raw.set_channel_types(ch_types_mapping)
                raw.set_montage(make_standard_montage("easycap-M10"), match_case=False)
                
                # we can already create the raw audio stimulus record
                audio_name = f"DownTheRabbitHoleFinal_SoundFile{segment}"
                stimuli = [
                    StimulusRecord(
                        modality="audio",
                        name=audio_name,
                        data_fn=self._make_audio_loader(audio_name),
                        is_attended=True,
                        feature_name="audio",
                    ),
                    StimulusRecord(
                    modality="audio",
                    name=audio_name,
                    data_fn=self._make_textgrid_loader(segment),
                    is_attended=True,
                    feature_name="textgrid"
            )
                ]

                try:
                    neural_fn = self._make_eeg_loader(
                        raw=raw,
                        onset_s=onset,
                        duration_s=self.stim_info[segment][0],
                    )
                except Exception as e:
                    print(f"Skipping {sub} segment {segment} due to error: {e}")
                    continue

                yield TrialRecord(
                    subject=sub_idx,
                    session=self.SESSION,
                    trial=segment,
                    condition="natural",  # all are natural speech in this dataset
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=neural_fn,
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------ Lazy loader makers ------------------------------

    def _make_audio_loader(self, audio_name: str) -> Callable[[], Dict[str, Any]]:
        """
        Load audiobook WAV (standardised if available; else raw).
        Returns {'fs': int, 'data': np.ndarray[1, T]}.
        """
        wav_path = os.path.join(self.download_dir, "audio", f"{audio_name}.wav")

        def _loader() -> Dict[str, Any]:
            fs, audio = wavfile.read(wav_path)
            if audio.ndim == 1:
                audio = audio[None, :]
            else:
                audio = audio.mean(axis=1, keepdims=True).T  # mono
            return {"fs": int(fs), "data": audio}
        return _loader

    def _make_eeg_loader(self, raw: BaseRaw, onset_s: float, duration_s: float) -> Callable[[], BaseRaw]:

        raw_copy = raw.copy()
        raw_copy.crop(max(onset_s, 0), min(onset_s + duration_s, raw.times[-1]))
        if onset_s < 0:
            # this is a bit hacky; mne doesn't support appending mne.io.brainvision.brainvision.RawBrainVision and mne.io.array.array.RawArray even though these are both BaseRaw...
            n_prepend = int(np.abs(onset_s) * self.FS_EEG)
            prepend_data = np.zeros((raw_copy.info["nchan"], n_prepend))
            data = np.concatenate([prepend_data, raw_copy.get_data()], axis=1)
            raw_copy = RawArray(data, raw_copy.info, verbose="ERROR")

        def _loader() -> BaseRaw:
            return raw_copy.load_data()

        return _loader
    
    def _make_textgrid_loader(self, segment: int) -> Callable[[], Dict[str, Any]]:

        words_csv_path = os.path.join(self.download_dir, "AliceChapterOne-EEG.csv")
        df = pd.read_csv(words_csv_path)

        segment_df = df[df['Segment'] == segment]

        words_dict = {
            "item": segment_df['Word'].tolist(),
            "onset_s": segment_df['onset'].tolist(),
            "offset_s": segment_df['offset'].tolist()
        }

        def _loader():
            return multi_tier_dict_to_textgrid({"words": words_dict})
        
        return _loader
    
    # ------------------------ Utils ------------------------------

    def _discover_raw_recordings(self):
        return sorted(
            glob.glob(os.path.join(self.download_dir, "S*.vhdr"))
        )
        
    def get_audiobook_paths(self):
        audiobooks_dir = os.path.join(self.download_dir, "audio")
        audiobook_names = [f"DownTheRabbitHoleFinal_SoundFile{p}.wav" for p in range(1, 13)]
        return [os.path.join(audiobooks_dir, name) for name in audiobook_names]
    
    def _get_audiobook_envelopes_and_durations(self):
        """
        Best guess at the "envelope" encoded in the stimtrack channel: full-wave rectified audio (seems closer to 
        E-prime triggers than half-wave rectified audio or hilbert envelope).
        We filter the envelope below 200 Hz since this is the hardware cutoff of the actiCHamp system.
        """
        
        data = {}
        for i, ab in enumerate(self.get_audiobook_paths(), 1):
            sr, wav_data = wavfile.read(ab)
            duration = wav_data.shape[0] / sr

            # env = wav_data * (wav_data>0) # half-wave rectification
            env = np.abs(wav_data) # full-wave rectification
            # env = np.abs(hilbert(wav_data)) # hilbert envelope

            # downsample and lowpass filter
            env = resample_poly(env.astype(float), self.FS_EEG, sr)
            env = filter_data(env, self.FS_EEG, 1, 200)

            data[i] = (duration, env)

        return data

    def _get_onset(self, raw, sub_idx, segment, method):

        if method == "annot":
            desc = raw.annotations.description
            event_idxs = [i for i, d in enumerate(desc) if d.startswith("Stimulus/")]
            segments = [d.replace("Stimulus/", "") for d in desc if d.startswith("Stimulus")]
            segments = [int(s.replace("S ", "")) for s in segments] # some subjects have descriptions Stimulus/1 etc, some Stimulus/S 1 etc.
            if segment not in segments:
                return None
            
            events, _ = mne.events_from_annotations(raw, verbose=False)
            onsets = events[event_idxs, 0]
            onset = onsets[segments.index(segment)] / raw.info["sfreq"]

            # account for E-Prime delays
            if segment == 1:
                onset += 0.06
            else:
                onset += 0.05
            return onset
        
        elif method == "crosscorr":
            if sub_idx in self.NOISY_OR_NO_STIMTRACK:
                return None
            
            for ch in ["Aux5", "AUD"]:
                if ch in raw.ch_names:
                    stim_channel = ch

            stim_data = raw.copy().pick_channels([stim_channel]).load_data().filter(1, None).get_data().squeeze()
            _, env = self.stim_info[segment]
            corr = correlate(stim_data, env, mode="full")
            lags = correlation_lags(len(stim_data), len(env), mode="full")
            lag = lags[np.argmax(corr)]
            onset = lag / raw.info["sfreq"]
            return onset
        
        else:
            raise ValueError(f"Unknown alignment method: {method}")

ADAPTOR = Brennan2018Adaptor
