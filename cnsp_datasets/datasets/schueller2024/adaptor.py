from __future__ import annotations

import os, glob
import numpy as np

from scipy.io import wavfile
from scipy.signal import resample_poly, hilbert
from scipy.stats import zscore
from mne.io import read_raw_fif, BaseRaw

from typing import Iterable, Callable, Any, Dict, List, Tuple
from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Schueller2024MEGAdaptor:
    """
    Emits TrialRecord objects for the Schueller (2024) MEG dataset.

    Expected layout:
      <root>/Set1/Audio/attended_speech/audiobook{1|3}_*.wav
      <root>/Set1/Audio/ignored_speech/audiobook{2|4}_*.wav
      <root>/Set*/<subject>/<HP_speaker_attended|LP_speaker_attended>/data_meg.fif

    For each MEG run, we:
      - detect attended speaker (HP/LP) from the parent folder,
      - build 5 trials by slicing the Raw using audio segment durations,
      - attach attended+ignored stimuli per trial.
    """

    def __init__(self, download_dir: str, set_glob: str = "Set*"):
        self.root = download_dir
        self.set_glob = set_glob

        # discover MEG files
        pat = os.path.join(self.root, self.set_glob, "**", "data_meg.fif")
        self._meg_files = sorted(glob.glob(pat, recursive=True))
        if not self._meg_files:
            raise FileNotFoundError(f"No MEG FIF found under {pat}")

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Emit one TrialRecord per (run x trial). Trials are 1..5.
        Subject id & trial index inferred from folder names/order.
        """
        for fif_path in self._meg_files:
            attended_speaker = self._infer_attended_speaker(fif_path)  # "HP" or "LP"
            subject = self._infer_subject_id(fif_path)                 # int (best effort)

            condition = f"{attended_speaker}_speaker_attended"

            # compute trial (start,end) boundaries from audio durations
            boundaries = self._trial_boundaries(attended_speaker)

            # one Raw reader per run (lazy per TrialRecord)
            for trial_idx, (t0, t1) in enumerate(boundaries, start=1):
                # stimuli (attended + ignored audio)
                att_name, att_paths = self._audio_paths(attended_speaker, trial_idx, stream="attended")
                ign_name, ign_paths = self._audio_paths(attended_speaker, trial_idx, stream="ignored")

                stimuli = [
                    StimulusRecord("audio", att_name, self._make_audio_loader(att_paths), True,  feature_name="audio"),
                    StimulusRecord("audio", ign_name, self._make_audio_loader(ign_paths), False, feature_name="audio"),
                ]

                yield TrialRecord(
                    subject=subject,
                    session=1,
                    trial=trial_idx,
                    condition=condition,
                    ns_type="meg",
                    stimulus=stimuli,
                    neural_data_fn=self._make_meg_loader(fif_path, t0, t1),
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # --------------------------- Audio helpers ---------------------------

    def _att_ign_audiobook_ids(self, attended_speaker: str) -> Tuple[int, int]:
        # As per your logic: HP -> attended 3 / ignored 2; LP -> attended 1 / ignored 4
        if attended_speaker == "HP":
            return 3, 2
        return 1, 4

    def _audio_glob(self, stream: str, audiobook_id: int) -> str:
        # stream in {"attended_speech","ignored_speech"}
        return os.path.join(self.root, "Set1", "Audio", stream, f"audiobook{audiobook_id}_*.wav")

    def _audio_paths(self, attended_speaker: str, trial: int, stream: str) -> Tuple[str, List[str]]:
        att_id, ign_id = self._att_ign_audiobook_ids(attended_speaker)
        if stream == "attended":
            abook = att_id
        else:
            abook = ign_id
        # names like "hp_audiobook3_01.wav"
        name = f"{attended_speaker.lower()}_audiobook{abook}_{trial:02d}.wav"
        wavs = sorted(glob.glob(self._audio_glob(
            "attended_speech" if stream == "attended" else "ignored_speech", abook)))
        if not wavs:
            raise FileNotFoundError(f"No WAVs for {stream} audiobook{abook} under Set1/Audio")
        return name, wavs

    def _concat_audio(self, wav_paths_key: Tuple[str, ...]) -> Tuple[int, np.ndarray]:
        """Read, z-score and concatenate a set of WAV chunks."""
        chunks = []
        fs0 = None
        for p in wav_paths_key:
            fs, x = wavfile.read(p)
            if fs0 is None:
                fs0 = fs
            elif fs0 != fs:
                raise ValueError(f"Sample rate mismatch: {fs0} vs {fs} in {p}")
            if x.ndim == 2:  # take first channel if stereo
                x = x[:, 0]
            chunks.append(zscore(x.astype(float), axis=None))
        audio = np.concatenate(chunks, axis=0).astype(np.float32)
        return fs0, audio

    def _make_audio_loader(self, wav_paths: List[str]) -> Callable[[], Dict[str, Any]]:
        key = tuple(wav_paths)
        def _loader() -> Dict[str, Any]:
            fs, audio = self._concat_audio(key)
            return {"fs": int(fs), "data": audio[None, :]}
        return _loader

    # --------------------------- MEG helpers ---------------------------

    def _make_meg_loader(self, fif_path: str, t0: float, t1: float) -> Callable[[], BaseRaw]:
        """Lazy: read FIF (preload=False) and crop to [t0, t1]."""
        def _loader() -> BaseRaw:
            raw = read_raw_fif(fif_path, preload=False, verbose="ERROR")
            # You can add .pick("meg") here if desired:
            # raw = raw.pick("meg")
            tmax = raw.times[-1]
            return raw.copy().crop(tmin=t0, tmax=min(t1, tmax))
        return _loader

    # --------------------------- Boundaries & inference ---------------------------

    def _trial_boundaries(self, attended_speaker: str) -> List[Tuple[float, float]]:
        """
        Compute 5 contiguous (start, end) times (in seconds) using attended vs ignored
        durations per trial. Uses the **max** of the two for each trial (as in your code).
        """
        att_id, ign_id = self._att_ign_audiobook_ids(attended_speaker)

        # collect per-trial durations by reading the *trial-specific* files
        durs: List[float] = []
        for trial in range(1, 6):
            # grab a representative WAV for the trial (pattern audiobookX_YY.wav)
            pat_att = os.path.join(self.root, "Set1", "Audio", "attended_speech", f"audiobook{att_id}_{trial:02d}.wav")
            pat_ign = os.path.join(self.root, "Set1", "Audio", "ignored_speech",  f"audiobook{ign_id}_{trial:02d}.wav")
            # If the dataset stores per-trial chunks, prefer them; else fall back to max of whole sets
            cand = []
            for pat in (pat_att, pat_ign):
                files = glob.glob(pat)
                if files:
                    fs, x = wavfile.read(files[0])
                    if x.ndim == 2:
                        x = x[:, 0]
                    cand.append(len(x) / fs)
            if cand:
                durs.append(max(cand))
            else:
                # fallback: compute from full concatenations (rare)
                att_all = sorted(glob.glob(self._audio_glob("attended_speech", att_id)))
                ign_all = sorted(glob.glob(self._audio_glob("ignored_speech",  ign_id)))
                fsA, aA = self._concat_audio(tuple(att_all))
                fsI, aI = self._concat_audio(tuple(ign_all))
                total = max(len(aA) / fsA, len(aI) / fsI)
                durs = _split_evenly(total, 5)
                break

        # turn durations into cumulative boundaries
        bounds: List[Tuple[float, float]] = []
        start = 0.0
        for d in durs[:5]:
            end = start + float(d)
            bounds.append((start, end))
            start = end
        return bounds

    def _infer_attended_speaker(self, fif_path: str) -> str:
        parent = os.path.basename(os.path.dirname(fif_path))
        if parent == "HP_speaker_attended":
            return "HP"
        if parent == "LP_speaker_attended":
            return "LP"
        raise ValueError(f"Cannot infer attended speaker from folder name: {parent}")

    def _infer_subject_id(self, fif_path: str) -> int:
        # try parent directory two levels up (Set1/<subject>/HP_speaker_attended/data_meg.fif)
        maybe = os.path.basename(os.path.dirname(os.path.dirname(fif_path)))
        try:
            return int(maybe)
        except ValueError:
            # fallback: 1-based index by file order
            return self._meg_files.index(fif_path) + 1


def _split_evenly(total_seconds: float, n: int) -> List[float]:
    d = float(total_seconds) / n
    return [d] * n


ADAPTOR = Schueller2024MEGAdaptor