from mne.io import BaseRaw


def set_raw_sfreq(raw: BaseRaw, sfreq: float) -> None:
    """
    Update sfreq (and lowpass) on a Raw object in-place using MNE's _unlock() API.
    Call after any operation that changes the number of time samples.
    """
    with raw.info._unlock():
        raw.info["sfreq"] = float(sfreq)
        raw.info["lowpass"] = min(raw.info["lowpass"], sfreq / 2.0)
