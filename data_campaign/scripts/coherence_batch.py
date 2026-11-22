"""
Neural-envelope coherence for the 2026-11-22 batches (new datasets), in the style of coherence_all.py, at 128 Hz or
at each dataset's native rate.

Welch coherence of eeg-envelope-coherence-neuroimage (Hann windows of 5 s, 4 s overlap, at either rate), EEG
average-referenced (MEG magnetometers unreferenced). Envelope: Hilbert envelope of the audio, or the shipped envelope,
resampled to the analysis rate. Complex coherency per trial is averaged over each subject's trials (duration-weighted),
complex-averaged over subjects, then |.| and channel-mean. Null: N_NULL (default 1) global circular shifts of the
envelope per trial, pooled the same way (enough to show the noise level). Cache per trial (resumable).
Usage: coherence_batch.py <out_dir> <128|native> [names...]   (env COHERENCE_THREADS, COHERENCE_NULL)
"""
import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, "/home/gu08wuvu/eeg-envelope-coherence-neuroimage/src")
sys.path.insert(0, "/home/gu08wuvu/cnsp_datasets_dev")
from coherence.coherence import (coherence_from_prep, null_coherence_shuffled_windows_from_prep,  # noqa: E402
                                 prepare_coherence)
from scipy.fft import next_fast_len  # noqa: E402
from scipy.signal import hilbert  # noqa: E402

from cnsp_datasets.preprocess.base import get_stim_array  # noqa: E402
from cnsp_datasets.preprocess.stimulus import ResampleStimulus  # noqa: E402
from cnsp_datasets.standardise.flat_sink import FlatSourceV1  # noqa: E402
from cnsp_datasets.validate.load import load_neural, resampled  # noqa: E402

N_NULL = int(os.environ.get("COHERENCE_NULL", 1))
THREADS = int(os.environ.get("COHERENCE_THREADS", 3))
T = "/data_storage/gu08wuvu/datasets/tmp/review"


def flat(dataset, keep=lambda r: True):
    return lambda: [r for r in FlatSourceV1(f"{T}/{dataset}/standardised", assume_first_attended=True).iter_trials()
                    if keep(r)]


def cond(*names):
    return lambda r: r.condition in names


def herrmann_snr(lo, hi):
    def keep(r):
        snr = next((float(m[1]) for s in r.stimulus if (m := re.search(r"_L(-?[0-9.]+)$", s.name))), None)
        return r.condition == "babble" and snr is not None and lo <= snr <= hi
    return keep


DATASETS = {  # name: (records, picks, reference, stimulus: attended | ignored, native fs)
    "harshaiyahav2025_attended": (flat("harshaiyahav2025"), "eeg", "average", "attended", 100),
    "harshaiyahav2025_ignored": (flat("harshaiyahav2025"), "eeg", "average", "ignored", 100),
    "herrmann2025_clear": (flat("herrmann2025", cond("clear")), "eeg", "average", "attended", 1024),
    "herrmann2025_babble": (flat("herrmann2025", cond("babble")), "eeg", "average", "attended", 1024),
    "herrmann2025_babble_hiSNR": (flat("herrmann2025", herrmann_snr(23, 60)), "eeg", "average", "attended", 1024),
    "herrmann2025_babble_midSNR": (flat("herrmann2025", herrmann_snr(2, 20)), "eeg", "average", "attended", 1024),
    "herrmann2025_babble_lowSNR": (flat("herrmann2025", herrmann_snr(-7, -1)), "eeg", "average", "attended", 1024),
    "holtze2021_attended": (flat("holtze2021"), "eeg", "average", "attended", 500),
    "holtze2021_ignored": (flat("holtze2021"), "eeg", "average", "ignored", 500),
    "momenian2024": (flat("momenian2024"), "eeg", "average", "attended", 1000),
    "habersetzer2025_audiobook1": (flat("habersetzer2025", cond("audiobook1")), "mag", None, "attended", 1000),
    "habersetzer2025_audiobook2": (flat("habersetzer2025", cond("audiobook2")), "mag", None, "attended", 1000),
    "pkueeg2025_day1": (flat("pkueeg2025", lambda r: r.session == 1), "eeg", "average", "attended", 1000),
    "pkueeg2025_day2": (flat("pkueeg2025", lambda r: r.session == 2), "eeg", "average", "attended", 1000),
    "pkueeg2025_day3": (flat("pkueeg2025", lambda r: r.session == 3), "eeg", "average", "attended", 1000),
    "wang2025_mixed": (flat("wang2025", cond("mixed")), "eeg", "average", "attended", 500),
    "wang2025_single-female": (flat("wang2025", cond("single-female")), "eeg", "average", "attended", 500),
    "wang2025_single-male": (flat("wang2025", cond("single-male")), "eeg", "average", "attended", 500),
    "yang2026_en": (lambda: list(FlatSourceV1(f"{T}/yang2026/standardised_en", assume_first_attended=True).iter_trials()),
                    "mag", None, "attended", 1000),
    "yang2026_ru": (lambda: list(FlatSourceV1(f"{T}/yang2026/standardised_ru", assume_first_attended=True).iter_trials()),
                    "mag", None, "attended", 1000),
    "yang2026_en_tsss": (lambda: [r for r in FlatSourceV1(f"{T}/yang2026/standardised_en",
                                                               assume_first_attended=True).iter_trials()
                                       if r.subject in (1, 2, 3, 4)],  # subset: tSSS costs ~7.5 min per trial
                         "mag", None, "attended", 1000,
                         ("/data_storage/gu08wuvu/datasets/tmp/review/yang2026/download/english-native-english-conversation/sss_cal_triux.dat",
                          "/data_storage/gu08wuvu/datasets/tmp/review/yang2026/download/english-native-english-conversation/ct_sparse_triux.fif")),
    "yang2026_ru_tsss": (lambda: [r for r in FlatSourceV1(f"{T}/yang2026/standardised_ru",
                                                               assume_first_attended=True).iter_trials()
                                       if r.subject in (1, 2, 3, 4)],  # subset: tSSS costs ~7.5 min per trial
                         "mag", None, "attended", 1000,
                         ("/data_storage/gu08wuvu/datasets/tmp/review/yang2026/download/russian-native-russian-conversation/sss_cal_vectorview.dat",
                          "/data_storage/gu08wuvu/datasets/tmp/review/yang2026/download/russian-native-russian-conversation/ct_sparse_vectorview.fif")),
    "wang2022": (flat("wang2022"), "mag", None, "attended", 1000),  # authors' tSSS data as shipped
}


def envelope(record, which, fs):
    # select by name: the flat format writes one token per feature, and only the first token is marked attended
    attended = next(s.name for s in record.stimulus if s.is_attended and s.modality == "audio")
    names = [s.name for s in record.stimulus if s.modality == "audio"]
    target = attended if which == "attended" else next(n for n in names if n != attended and not n.endswith("_babble"))
    stims = [s for s in record.stimulus if s.name == target
             and (s.feature_name == "audio" or s.feature_name.startswith("envelope"))]
    stim = sorted(stims, key=lambda s: s.feature_name != "audio")[0]
    data = stim.data_fn()
    if stim.feature_name == "audio":
        x = np.atleast_2d(get_stim_array(data)).astype(float)  # padded to a fast length: scipy caches FFT plans
        data = {"fs": data["fs"], "data": np.abs(hilbert(x, N=next_fast_len(x.shape[-1]), axis=-1))[:, :x.shape[-1]]}
    return np.atleast_2d(get_stim_array(ResampleStimulus(fs).run(data))).mean(0)


def tsss_neural(record, picks, cal_ct):
    """Maxwell filtering (tSSS) in the analysis only, as the MEG validations: bads = FIF bads +
    find_bad_channels_maxwell on the first 120 s; st_duration 10 s; origin fitted; head frame."""
    import mne
    cal, ct = cal_ct
    raw = record.neural_data_fn()
    raw.load_data(verbose="ERROR")
    head = raw.copy().crop(0, min(120, raw.times[-1]))
    noisy, flat = mne.preprocessing.find_bad_channels_maxwell(head, calibration=cal, cross_talk=ct, verbose="ERROR")[:2]
    raw.info["bads"] = sorted(set(raw.info["bads"]) | set(noisy) | set(flat))
    raw = mne.preprocessing.maxwell_filter(raw, calibration=cal, cross_talk=ct, st_duration=10, origin="auto",
                                           coord_frame="head", verbose="ERROR")
    return raw.pick(picks)


def one_trial(item, name, picks, reference, which, fs, cal_ct=None):
    i, r = item
    try:
        raw = tsss_neural(r, picks, cal_ct) if cal_ct else load_neural(r, picks, reference)
        x, fs = resampled(raw, fs)  # never upsamples: analyse at the rate the neural data end up at
        env = envelope(r, which, fs)
    except Exception as e:  # noqa: BLE001 - logged and skipped
        print(f"{name}: trial {i + 1} (sub {r.subject}) FAILED: {type(e).__name__}: {e}", flush=True)
        return None
    sd = x.std(axis=1)
    live = sd > 1e-6 * np.median(sd)  # drop flat channels not marked bad (0/0 -> NaN coherence; yang2026 notes 12)
    if not live.all():
        x = x[live]
        raw.drop_channels([c for c, ok in zip(raw.ch_names, live) if not ok])
    nperseg, noverlap = 5 * fs, 4 * fs
    n = min(len(env), x.shape[1])
    if n < 2 * nperseg:
        return None
    min_shift = min(30.0, (n / fs - 5) / 4)
    prep = prepare_coherence(x[:, :n].T, env[:n, None], fs=fs, nperseg=nperseg, noverlap=noverlap)
    c = coherence_from_prep(prep)
    null = null_coherence_shuffled_windows_from_prep(prep, N_NULL, min_shift_seconds=min_shift, mode="global_shift",
                                                     rng=i)[:, :, :, 0]
    w = prep.x_spectrum.n_frames
    print(f"{name}: trial {i + 1} (sub {r.subject}) done", flush=True)
    return r.subject, tuple(raw.ch_names), w, c.freqs, (w * c.Cxy[:, :, 0]).astype(np.complex64), \
        (w * null).astype(np.complex64)


def cached_trial(item, name, picks, reference, which, fs, out, cal_ct=None):
    path = f"{out}/cache/{name}/{item[0]}.npz"
    if os.path.exists(path):
        d = np.load(path)
        return int(d["sub"]), tuple(d["names"]), int(d["w"]), d["freqs"], d["wc"], d["wnull"]
    res = one_trial(item, name, picks, reference, which, fs, cal_ct)
    if res is not None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sub, names, w, freqs, wc, wnull = res
        np.savez(path + ".tmp.npz", sub=sub, names=np.array(names), w=w, freqs=freqs, wc=wc, wnull=wnull)
        os.replace(path + ".tmp.npz", path)
    return res


def run(name, out, mode):
    get_records, picks, reference, which, native, *cal_ct = DATASETS[name]
    cal_ct = cal_ct[0] if cal_ct else None
    fs = min(128, native) if mode == "128" else native  # no upsampling (harshaiyahav2025: 100 Hz in both)
    records = get_records()
    print(f"=== {name}: {len(records)} trials at {fs} Hz", flush=True)
    acc = defaultdict(lambda: [0.0, 0, 0])
    freqs, channels = None, {}
    with ThreadPoolExecutor(THREADS) as pool:
        for res in pool.map(lambda it: cached_trial(it, name, picks, reference, which, fs, out, cal_ct),
                            enumerate(records)):
            if res is None:
                continue
            sub, names, w, freqs, wc, wnull = res
            channels[sub] = names
            a = acc[sub]
            a[0] += w
            a[1] = a[1] + wc
            a[2] = a[2] + wnull
    subs = sorted(acc)
    common = [c for c in channels[subs[0]] if all(c in channels[s] for s in subs)]
    keep = {s: [channels[s].index(c) for c in common] for s in subs}
    per_subject = np.array([acc[s][1][:, keep[s]] / acc[s][0] for s in subs])
    per_subject_null = np.array([acc[s][2][..., keep[s]] / acc[s][0] for s in subs])
    real_mean = np.abs(per_subject.mean(0)).mean(1)
    null_mean = np.abs(per_subject_null.mean(0)).mean(2)  # (n_null, F)
    np.savez(f"{out}/{name}.npz", freqs=freqs, real_mean=real_mean, null_mean=null_mean,
             per_subject_abs=np.abs(per_subject).mean(2), subjects=subs, fs=fs)
    null_ref = null_mean.mean(0)
    band = lambda a, b: (freqs >= a) & (freqs <= b)  # noqa: E731
    edges = [(0.2, 1), (1, 4), (4, 8), (8, 15), (15, 30), (30, 60), (60, 120), (120, 250), (250, 500)]
    summary = dict(name=name, fs=fs, n_null=N_NULL, n_subjects=len(subs), n_channels=len(common),
                   n_trials=len(records), ratio_to_null={f"{a}-{b} Hz": float((real_mean[band(a, b)] /
                                                                               null_ref[band(a, b)]).mean())
                                                         for a, b in edges if b <= fs / 2})
    json.dump(summary, open(f"{out}/{name}.json", "w"), indent=1)
    panels = [(min(fs / 2, 64), True), (15, False)] + ([(fs / 2, True)] if fs > 128 else [])
    fig, axs = plt.subplots(1, len(panels), figsize=(6 * len(panels), 4), layout="constrained")
    for ax, (fmax, logy) in zip(axs, panels):
        k = (freqs > 0) & (freqs <= fmax)
        for j, nm in enumerate(null_mean):
            ax.plot(freqs[k], nm[k], color="#a3a29c", lw=1, label="surrogate (global shift)" if j == 0 else None)
        ax.plot(freqs[k], real_mean[k], color="#2a78d6", lw=1.6 if fmax <= 64 else 1,
                label=f"complex mean over {len(subs)} subjects")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel("frequency (Hz)", color="#52514e")
        ax.set_ylabel("channel-mean |coherency|", color="#52514e")
        ax.grid(alpha=0.25, lw=0.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(f"{name}: neural-envelope coherence ({fs} Hz, 5 s Hann windows, 4 s overlap)", x=0.01, ha="left",
                 fontsize=11)
    fig.savefig(f"{out}/{name}.png", dpi=110)
    plt.close(fig)
    print(f"=== {name} summary: {json.dumps(summary['ratio_to_null'])}", flush=True)


if __name__ == "__main__":
    out, mode = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for name in sys.argv[3:] or DATASETS:
        try:
            run(name, out, mode)
        except Exception as e:  # noqa: BLE001 - keep going
            print(f"=== {name} FAILED: {type(e).__name__}: {e}", flush=True)
