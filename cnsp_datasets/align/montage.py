import mne
import numpy as np
from mne.channels import DigMontage
from mne.channels.interpolation import _make_interpolation_matrix
from mne.io import BaseRaw

from cnsp_datasets.preprocess.base import NeuralPreprocStep


def _positions(info: mne.Info, origin: np.ndarray) -> np.ndarray:
    pos = np.array([ch["loc"][:3] for ch in info["chs"]]) - origin
    if not np.all(np.isfinite(pos)) or np.any(np.linalg.norm(pos, axis=1) == 0):
        missing = [ch["ch_name"] for ch, p in zip(info["chs"], pos + origin) if not np.any(p) or not np.all(np.isfinite(p))]
        raise ValueError(f"Channels without positions: {missing}")
    return pos


def montage_interpolation_matrix(
        info_from: mne.Info,
        montage_to: DigMontage,
        alpha: float = 1e-5,
        ) -> tuple[np.ndarray, list[str]]:
    '''
    Spherical-spline interpolation matrix (as used by MNE's interpolate_bads) mapping the EEG
    channels in info_from onto the channels of montage_to.

    Both sets of positions are taken in MNE's head frame and centred on a sphere fitted to the
    source electrodes, so the source recording must have a montage set.

    Returns (matrix, ch_names) where matrix has shape (len(ch_names), n_channels_from), so that
    eeg_to = matrix @ eeg_from.
    '''
    info_to = mne.create_info(montage_to.ch_names, sfreq=info_from["sfreq"], ch_types="eeg")
    info_to.set_montage(montage_to, verbose="ERROR")

    _, origin, _ = mne.bem.fit_sphere_to_headshape(info_from, dig_kinds=("eeg",), units="m", verbose="ERROR")

    matrix = _make_interpolation_matrix(_positions(info_from, origin), _positions(info_to, origin), alpha=alpha)
    return matrix.astype(np.float32), info_to.ch_names


def pick_montage(montage: DigMontage, ch_names: list[str]) -> DigMontage:
    '''Montage with only ch_names (in that order), keeping the fiducials so positions are unchanged.'''
    pos = montage.get_positions()
    missing = [ch for ch in ch_names if ch not in pos["ch_pos"]]
    if missing:
        raise ValueError(f"Channels not in montage: {missing}")
    return mne.channels.make_dig_montage(
        ch_pos={ch: pos["ch_pos"][ch] for ch in ch_names},
        nasion=pos["nasion"], lpa=pos["lpa"], rpa=pos["rpa"], coord_frame=pos["coord_frame"],
    )


class InterpolateToMontage(NeuralPreprocStep):
    '''
    Maps the good EEG channels of a Raw onto the channels of `montage` (spherical splines), dropping
    all other channels. Bad channels are left out of the source, so target channels at their
    positions are interpolated from their neighbours.

    With average_reference=True, the output is re-referenced to the average of the target channels,
    so recordings with different references (e.g. BioSemi vs mastoid) end up comparable.

    Example:
        InterpolateToMontage(pick_montage(make_standard_montage("standard_1020"), ["Fz", "Cz", "Pz"]))
    '''

    def __init__(self, montage: DigMontage, alpha: float = 1e-5, average_reference: bool = False):
        self.montage = montage
        self.alpha = alpha
        self.average_reference = average_reference

    def run(self, raw: BaseRaw) -> BaseRaw:
        good = raw.copy().pick("eeg", exclude="bads")
        matrix, ch_names = montage_interpolation_matrix(good.info, self.montage, alpha=self.alpha)
        data = matrix @ good.get_data()
        if self.average_reference:
            data -= data.mean(axis=0, keepdims=True)

        info = mne.create_info(ch_names, raw.info["sfreq"], ch_types="eeg")
        out = mne.io.RawArray(data, info, verbose="ERROR")
        out.set_montage(self.montage, verbose="ERROR")
        out.set_meas_date(raw.info["meas_date"])  # annotations are timed relative to it
        out.set_annotations(raw.annotations)
        return out

    def __repr__(self) -> str:
        return (f"InterpolateToMontage({len(self.montage.ch_names)} channels, alpha={self.alpha:g}, "
                f"average_reference={self.average_reference})")
