import copy
import random
import warnings
from typing import Iterable

import numpy as np
import torch
from scipy.stats import zscore
from torch.utils.data import Dataset, ConcatDataset
from tqdm import tqdm

from cnsp_datasets.preprocess.base import get_stim_array
from cnsp_datasets.preprocess.neural import ResampleNeural
from cnsp_datasets.preprocess.stimulus import HilbertEnvelope, ResampleStimulus
from cnsp_datasets.standardise.trial_record import TrialRecord


class SessionDataset(Dataset):

    def __init__(
            self,
            record: TrialRecord,
            fs: int = 512,
            eeg_steps: list | None = None,
            stim_steps: list | None = None,
            stim_feature: str = "audio",
            picks: str | list = "eeg",
            segment_length: float = 5.0,
            hop_length: float = 1.0,
            mismatch_offset: float | str = 6.0,
            stim_cache: dict | None = None,
            ):
        '''
        Match-mismatch dataset for a single EEG trial, loaded and preprocessed from a TrialRecord
        (e.g. from FlatSourceV1(standardised_dir).iter_trials()).

        Each item is (eeg_segment, matched_segment, mismatched_segment), float32 tensors of shape
        (channels, samples). The mismatched segment is taken from the same stimulus at a different time.

        inputs:
        - record: the trial to load.
        - fs: sample rate (Hz) that both EEG and stimulus must have after preprocessing.
        - eeg_steps: NeuralPreprocStep list applied to the (picked) Raw. Default: [ResampleNeural(fs)].
        - stim_steps: StimulusPreprocStep list applied to the stimulus. Default: Hilbert envelope, then
          ResampleStimulus(fs).
        - stim_feature: feature_name of the stimulus to load from the record.
        - picks: channels to keep, passed to raw.pick() before preprocessing. Default drops non-EEG
          channels (e.g. the misc-typed mastoids in accou2023); None keeps every channel.
          (ClassifierSpec.session_kwargs sets eeg_steps, stim_steps and picks for a classifier.)
        - segment_length: length of each segment, in seconds.
        - hop_length: distance between consecutive window onsets, in seconds.
        - mismatch_offset: onset of the mismatched segment relative to the matched one, in seconds,
          or 'random' for a random segment of the same stimulus (it may overlap the matched one).
        - stim_cache: dict shared between sessions so each stimulus is only preprocessed once.
        '''

        super().__init__()

        self.fs = fs
        self.subject = record.subject
        self.trial = record.trial
        self.condition = record.condition

        eeg_steps = [ResampleNeural(fs)] if eeg_steps is None else eeg_steps
        stim_steps = [HilbertEnvelope(), ResampleStimulus(fs)] if stim_steps is None else stim_steps

        stims = [s for s in record.stimulus if s.feature_name == stim_feature]
        if not stims:
            raise ValueError(f"No '{stim_feature}' stimulus in trial sub-{record.subject} trial-{record.trial}")
        stim = stims[0]
        self.stimulus_name = stim.name

        self.info = None  # channel names and positions of the preprocessed EEG, set by _load_eeg
        self.eeg = self._load_eeg(record, eeg_steps, picks)
        self.story = self._load_stimulus(stim, stim_steps, stim_cache)

        # EEG and stimulus are aligned at onset; trim whichever runs longer
        n_samples = min(self.eeg.shape[-1], self.story.shape[-1])
        if abs(self.eeg.shape[-1] - self.story.shape[-1]) > fs:
            raise ValueError(
                f"EEG ({self.eeg.shape[-1]}) and stimulus ({self.story.shape[-1]}) lengths differ by more "
                f"than 1 s for sub-{record.subject} trial-{record.trial}"
            )
        self.eeg = zscore(self.eeg[:, :n_samples], axis=-1).astype(np.float32)
        self.story = zscore(self.story[:, :n_samples], axis=-1).astype(np.float32)

        self.segment_length = round(segment_length * fs)
        self.hop_length = round(hop_length * fs)
        self.mismatch_offset = mismatch_offset if mismatch_offset == 'random' else round(mismatch_offset * fs)

    def _load_eeg(self, record, steps, picks):
        raw = record.neural_data_fn()
        raw.load_data(verbose="ERROR")
        if picks is not None:
            raw.pick(picks)
        for step in steps:
            raw = step.run(raw)
        if raw.info["sfreq"] != self.fs:
            raise ValueError(f"EEG is at {raw.info['sfreq']} Hz after preprocessing, expected {self.fs} Hz")
        self.info = raw.info
        return raw.get_data()

    def _load_stimulus(self, stim, steps, cache):
        key = (stim.modality, stim.name, stim.feature_name, repr(steps))
        if cache is not None and key in cache:
            return cache[key]

        data = stim.data_fn()
        for step in steps:
            data = step.run(data)
        if data["fs"] != self.fs:
            raise ValueError(f"Stimulus is at {data['fs']} Hz after preprocessing, expected {self.fs} Hz")

        story = np.atleast_2d(get_stim_array(data)).astype(np.float32)
        if cache is not None:
            cache[key] = story
        return story

    def time_split(self, start: float, end: float) -> "SessionDataset":
        '''
        Return a view of this session restricted to [start, end), given as fractions of its duration.
        Arrays are shared, not copied, so train/val/test splits of a session cost no extra memory.
        '''
        n_samples = self.eeg.shape[-1]
        a, b = round(start * n_samples), round(end * n_samples)
        view = copy.copy(self)
        view.eeg = self.eeg[:, a:b]
        view.story = self.story[:, a:b]
        return view

    def __len__(self):
        n_samples = self.eeg.shape[-1]
        span = self.segment_length if self.mismatch_offset == 'random' else self.segment_length + self.mismatch_offset
        if n_samples < span:
            return 0
        return (n_samples - span) // self.hop_length + 1

    def __getitem__(self, index):
        if not 0 <= index < len(self):
            raise IndexError(index)

        matched_onset = index * self.hop_length

        if self.mismatch_offset == 'random':
            mismatched_onset = random.randint(0, self.eeg.shape[-1] - self.segment_length)
        else:
            mismatched_onset = matched_onset + self.mismatch_offset

        eeg_segment = self.eeg[:, matched_onset:matched_onset + self.segment_length]
        matched_segment = self.story[:, matched_onset:matched_onset + self.segment_length]
        mismatched_segment = self.story[:, mismatched_onset:mismatched_onset + self.segment_length]

        return (
            torch.from_numpy(eeg_segment),
            torch.from_numpy(matched_segment),
            torch.from_numpy(mismatched_segment),
        )


def load_sessions(records: Iterable[TrialRecord], on_error: str = "raise", **kwargs) -> list[SessionDataset]:
    '''
    Load and preprocess one SessionDataset per record. kwargs are passed to SessionDataset; stimuli
    shared between trials (e.g. the same audiobook heard by several subjects) are preprocessed once.
    on_error="skip" leaves out records that fail to load (with a warning) instead of raising.
    '''
    kwargs.setdefault("stim_cache", {})
    sessions = []
    for record in tqdm(list(records), desc="Loading sessions"):
        try:
            sessions.append(SessionDataset(record, **kwargs))
        except Exception as e:
            if on_error != "skip":
                raise
            warnings.warn(f"Skipped sub-{record.subject} trial-{record.trial}: {type(e).__name__}: {e}")
    return sessions


def split_sessions(
        sessions: list[SessionDataset],
        splits: dict[str, tuple[float, float]] = {"train": (0.0, 0.8), "val": (0.8, 0.9), "test": (0.9, 1.0)},
        ) -> dict[str, ConcatDataset]:
    '''
    Split every session in time (e.g. first 80% of each trial for training) and concatenate each
    split across sessions, so every subject and stimulus appears in every split.
    '''
    return {
        name: ConcatDataset([session.time_split(start, end) for session in sessions])
        for name, (start, end) in splits.items()
    }
