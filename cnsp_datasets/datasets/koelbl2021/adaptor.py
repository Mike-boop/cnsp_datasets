from __future__ import annotations

import os, glob
import numpy as np

from pathlib import Path
from scipy.io import wavfile
from scipy.signal import hilbert, correlate, correlation_lags
from scipy.stats import zscore
from mne.io import read_raw_bti, BaseRaw
from mne.filter import resample
from mne.channels import make_standard_montage

from typing import Iterable, Callable, Any, Dict, List, Tuple
from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Koelbl2021MEGAdaptor:

    def __init__(self, download_dir: str):
        self.root = download_dir

        self.meg_dirs = glob.glob(
            os.path.join(self.root, "P*")
        )
        self.wav_paths = glob.glob(
            os.path.join(self.root, "audios", "*.wav")
        )

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Emit one TrialRecord per (run x trial). Trials are 1..5.
        Subject id & trial index inferred from folder names/order.
        """
        for meg_dir in self.meg_dirs:
            meg_dir = Path(meg_dir)

            pdf_fname = meg_dir / 'c,rfhp1.0Hz'    # main MEG file
            config_fname = meg_dir / 'config'      # sensor layout/config
            head_shape_fname = meg_dir / 'hs_file' # head shape file

            raw = read_raw_bti(
                pdf_fname=pdf_fname,
                config_fname=config_fname,
                head_shape_fname=head_shape_fname,
                preload=False
            )
            stim_channel = raw.copy().pick_channels(['EXT 004']).get_data().squeeze()

            raw.drop_channels(
                ['EXT 001', 'EXT 002', 'EXT 003', 'EXT 004', 'EXT 005', 'EXT 006'] +\
                ['STI 013', 'STI 014', 'UTL 001']
            )

            # categorise and rename the EEG channels
            raw.set_channel_types({ch: 'eeg' for ch in raw.ch_names if ch.endswith('-1') or ch.startswith('EEG') and ch != "EEG 003"})
            raw.rename_channels(lambda x: x.replace("-1", "") if x.endswith("-1") else x)
            raw.set_montage(make_standard_montage('standard_1020'), match_case=False, on_missing='warn')

            for i, wavfile in enumerate(sorted(self.wav_paths), start=1):
                # stimuli (attended + ignored audio)
                audio_resampled = self._load_resample_audio(wavfile, raw.info['sfreq'])

                # get alignment via cross-correlation
                corr = correlate(stim_channel, audio_resampled, mode='same')
                lags = correlation_lags(len(stim_channel), len(audio_resampled), mode='same')
                onset_lag = lags[np.argmax(corr)]
                onset = onset_lag / raw.info['sfreq']
                duration = len(audio_resampled) / raw.info['sfreq']
                offset = onset+duration

                audio_name = os.path.basename(wavfile).replace(".wav", "").replace("_", "-")
                subject = int(meg_dir.name.replace("P", ""))
                trial_idx = i
                condition = "natural"


                stimuli = [
                    StimulusRecord("audio", audio_name, self._make_audio_loader(wavfile), True,  feature_name="audio"),
                ]

                yield TrialRecord(
                    subject=subject,
                    session=1,
                    trial=trial_idx,
                    condition=condition,
                    ns_type="meg",
                    stimulus=stimuli,
                    neural_data_fn=self._make_meg_loader(raw.copy(), onset, offset),
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # --------------------------- Audio helpers ---------------------------

    def _make_audio_loader(self, wav_path: List[str]) -> Callable[[], Dict[str, Any]]:
        def _loader() -> Dict[str, Any]:
            fs, audio = self._load_wav_file(wav_path)
            return {"fs": int(fs), "data": audio[None, :]}
        return _loader
    
    def _load_resample_audio(self, wav_path: str, target_fs: float) -> np.ndarray:
        """Load audio from wav_path and resample to target_fs."""
        fs, audio = self._load_wav_file(wav_path)
        resampled_audio = resample(audio, target_fs, fs)

        return resampled_audio
    
    def _load_wav_file(self, wav_path: str) -> Tuple[float, np.ndarray]:
        """Load a wav file and return its sampling frequency and audio data."""
        fs, audio = wavfile.read(wav_path)
        audio = audio[:, 0].astype(float)  # Use only the first channel if stereo
        return fs, audio


    # --------------------------- MEG helpers ---------------------------

    def _make_meg_loader(self, raw: BaseRaw, t0: float, t1: float) -> Callable[[], BaseRaw]:
        """Lazy: read FIF (preload=False) and crop to [t0, t1]."""
        def _loader() -> BaseRaw:
            tmax = raw.times[-1]
            print(t0, t1)
            return raw.load_data().crop(tmin=t0, tmax=min(t1, tmax))
        return _loader

ADAPTOR = Koelbl2021MEGAdaptor