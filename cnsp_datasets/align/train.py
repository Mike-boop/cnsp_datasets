import copy
import random
import time
from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F
from mne.channels import DigMontage
from torch.utils.data import DataLoader
from tqdm.auto import tqdm

from cnsp_datasets.align.classifiers import SimilarityDetector
from cnsp_datasets.align.dataset import SessionDataset, load_sessions, split_sessions
from cnsp_datasets.align.montage import montage_interpolation_matrix
from cnsp_datasets.preprocess.neural import MNERawMethod, ResampleNeural
from cnsp_datasets.standardise.trial_record import TrialRecord


def _mm_logits(model, eeg, matched, mismatched):
    return torch.cat([model(eeg, matched), model(eeg, mismatched)], dim=1)  # (batch, 2)


def _eeg_to_device(eeg, interp, device):
    eeg = eeg.to(device)
    return eeg if interp is None else interp @ eeg


@torch.no_grad()
def _evaluate(model, loader, interp, device):
    model.eval()
    n_correct, n_total, total_loss = 0, 0, 0.0
    for eeg, matched, mismatched in loader:
        eeg = _eeg_to_device(eeg, interp, device)
        matched, mismatched = matched.to(device), mismatched.to(device)
        logits = _mm_logits(model, eeg, matched, mismatched)
        target = torch.zeros(len(eeg), dtype=torch.long, device=device)
        total_loss += F.cross_entropy(logits, target, reduction="sum").item()
        n_correct += (logits.argmax(dim=1) == 0).sum().item()
        n_total += len(eeg)
    return total_loss / n_total, n_correct / n_total


def train_classifier(
        data: Iterable[TrialRecord] | list[SessionDataset],
        montage: DigMontage | None = None,
        fs: int = 1024,
        splits: dict[str, tuple[float, float]] = {"train": (0.0, 0.8), "val": (0.8, 0.9), "test": (0.9, 1.0)},
        eeg_steps: list | None = None,
        segment_length: float = 5.0,
        hop_length: float = 1.0,
        mismatch_offset: float | str = 6.0,
        model_kwargs: dict | None = None,
        batch_size: int = 64,
        epochs: int = 10,
        lr: float = 1e-3,
        interp_alpha: float = 1e-5,
        device: str | None = None,
        seed: int = 0,
        ) -> dict:
    '''
    Train and evaluate a match-mismatch classifier (SimilarityDetector), optionally on EEG
    interpolated onto `montage`.

    Each trial is split in time into train/val/test (`splits`, fractions of each trial). The model is
    trained with cross-entropy over (matched, mismatched) scores, the checkpoint with the best
    validation accuracy is kept, and its test accuracy is reported. The frequency band is whatever the
    sessions were preprocessed to (see ClassifierSpec for the broadband and high-frequency variants).

    inputs:
    - data: TrialRecords to load (e.g. from FlatSourceV1(dir).iter_trials()), or SessionDatasets that
      were already loaded at `fs` (so data can be reused across calls; their window settings are
      overwritten with segment_length, hop_length and mismatch_offset).
    - montage: channels the model sees. The recorded EEG is mapped onto them with a spherical-spline
      interpolation matrix, applied to each batch on the device. None (default) uses the sessions'
      channels as they are (e.g. when ClassifierSpec preprocessing already mapped them).
    - fs: sample rate for EEG and stimulus envelope.
    - eeg_steps: EEG preprocessing when loading records. Default: 0.5 Hz high-pass, resample to fs.
    - segment_length, hop_length, mismatch_offset: passed to SessionDataset (seconds).
    - model_kwargs: passed to SimilarityDetector. Default n_layers=6, which with kernel_size=3 gives a
      receptive field of 729 samples (~0.7 s at 1024 Hz).
    - interp_alpha: spline regularisation for `montage`. MNE's default 1e-5 is stable but smooths
      spatially, even where target and recorded channels coincide; ~1e-9 passes those channels through
      unchanged but can amplify noise on channels outside the recorded cap's coverage.

    Returns a dict with the trained model (best-on-val weights), its kwargs, per-epoch history, the
    model's channel names, and best validation and test accuracy (chance 0.5).
    '''
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    data = list(data)
    if all(isinstance(d, SessionDataset) for d in data):
        sessions = data
        if any(s.fs != fs for s in sessions):
            raise ValueError(f"Sessions were loaded at {sorted({s.fs for s in sessions})} Hz, expected {fs} Hz")
        for s in sessions:
            s.segment_length, s.hop_length = round(segment_length * fs), round(hop_length * fs)
            s.mismatch_offset = mismatch_offset if mismatch_offset == 'random' else round(mismatch_offset * fs)
    else:
        if eeg_steps is None:
            eeg_steps = [MNERawMethod("filter", l_freq=0.5, h_freq=None, verbose="ERROR"), ResampleNeural(fs)]
        sessions = load_sessions(
            data, fs=fs, eeg_steps=eeg_steps,
            segment_length=segment_length, hop_length=hop_length, mismatch_offset=mismatch_offset,
        )

    ch_names = sessions[0].info.ch_names
    if any(s.info.ch_names != ch_names for s in sessions):
        raise ValueError("All sessions must have the same EEG channels (in the same order)")
    if montage is None:
        interp, target_ch_names = None, ch_names
    else:
        interp, target_ch_names = montage_interpolation_matrix(sessions[0].info, montage, alpha=interp_alpha)
        interp = torch.from_numpy(interp).to(device)

    datasets = split_sessions(sessions, splits)
    loaders = {
        name: DataLoader(ds, batch_size=batch_size, shuffle=(name == "train"), drop_last=(name == "train"))
        for name, ds in datasets.items()
    }
    print(f"{len(sessions)} sessions | " + " | ".join(f"{name}: {len(ds)} windows" for name, ds in datasets.items())
          + f" | {len(ch_names)} -> {len(target_ch_names)} channels", flush=True)

    model_kwargs = {"n_layers": 6, **(model_kwargs or {})}
    model_kwargs.update(n_eeg_channels=len(target_ch_names), n_stimfeat_channels=sessions[0].story.shape[0])
    model = SimilarityDetector(**model_kwargs).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    history = []
    best_val_acc, best_state = -1.0, None
    for epoch in range(epochs):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        for eeg, matched, mismatched in tqdm(loaders["train"], desc=f"epoch {epoch}", leave=False):
            eeg = _eeg_to_device(eeg, interp, device)
            logits = _mm_logits(model, eeg, matched.to(device), mismatched.to(device))
            loss = F.cross_entropy(logits, torch.zeros(len(eeg), dtype=torch.long, device=device))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        val_loss, val_acc = _evaluate(model, loaders["val"], interp, device)
        history.append({"epoch": epoch, "train_loss": train_loss / len(loaders["train"]), "val_loss": val_loss,
                        "val_acc": val_acc, "seconds": time.time() - t0})
        print(f"epoch {epoch}: train loss {history[-1]['train_loss']:.3f} | val loss {val_loss:.3f} | "
              f"val acc {val_acc:.3f} | {history[-1]['seconds']:.0f} s", flush=True)

        if val_acc > best_val_acc:
            best_val_acc, best_state = val_acc, copy.deepcopy(model.state_dict())

    model.load_state_dict(best_state)
    _, test_acc = _evaluate(model, loaders["test"], interp, device)
    print(f"best val acc {best_val_acc:.3f} | test acc {test_acc:.3f} (chance 0.5)", flush=True)

    return {
        "model": model,
        "model_kwargs": model_kwargs,
        "history": history,
        "ch_names": target_ch_names,
        "best_val_acc": best_val_acc,
        "test_acc": test_acc,
    }
