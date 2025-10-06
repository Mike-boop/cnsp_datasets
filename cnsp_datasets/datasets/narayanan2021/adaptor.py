# nsptools/adapters/narayanan2021.py
from __future__ import annotations

import os, glob
import numpy as np
import pandas as pd
from typing import Iterable, Callable, Any, Dict, List, Tuple, Optional

from mne.io import read_raw_curry, BaseRaw
from mne.channels import make_dig_montage
from scipy.io import wavfile

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


# condition code → attended/unattended file stems + attended direction (ear)
COND_MAP: Dict[str, Dict[str, str]] = {
    "1L": {"attend": "part1_track2_dry", "unattend": "part1_track1_dry", "dir": "R"},
    "1R": {"attend": "part1_track1_dry", "unattend": "part1_track2_dry", "dir": "L"},
    "2L": {"attend": "part2_track1_dry", "unattend": "part2_track2_dry", "dir": "R"},
    "2R": {"attend": "part2_track2_dry", "unattend": "part2_track1_dry", "dir": "L"},
}
COND_TO_TRIAL = {"1L": 1, "1R": 2, "2L": 3, "2R": 4}


class Narayanan2021Adapter:
    """
    Adapter for Narayanan 2021 (EEG). Pure: no writes, all I/O is lazy.

    Expected layout (per your script):
      <root>/
        ├─ S*/ *.dat              (Curry EEG files; name like 'S07_something_1L.dat')
        └─ stimuli/ *dry.wav      (audio files used in the experiment)

    For each .dat:
      - Parse subject ID 'S##' and condition code in {'1L','1R','2L','2R'}.
      - Build TrialRecord:
          subject=<int>, session=1, trial=COND_TO_TRIAL[cond],
          condition=f"competing-f{dir}", ns_type="eeg"
      - Stimuli: two StimulusRecord entries (attended/unattended), feature_name="audio".
      - Neural loader: read_raw_curry(preload=False), crop to [onset, offset] computed
        from Trigger edges with +10 s extension, and drop 'Trigger','XtraL','XtraR' if present.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self._dat_files = self._discover_dat_files()
        self._audio_root = os.path.join(download_dir, "stimuli")

    # --------------------------- public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for dat_path in self._dat_files:
            print("parsing..." + dat_path)
            sub_id, cond = self._parse_subject_and_cond(dat_path)
            meta = COND_MAP[cond]
            trial_idx = COND_TO_TRIAL[cond]
            condition = f"competing-f{meta['dir']}"

            # stimuli (audio only; envelopes or resampling belong in canonicalizer)
            att_name = meta["attend"]
            un_name  = meta["unattend"]

            stimuli = [
                StimulusRecord(
                    modality="audio",
                    name=att_name,
                    data_fn=self._make_audio_loader(att_name),
                    is_attended=True,
                    feature_name="audio",
                ),
                StimulusRecord(
                    modality="audio",
                    name=un_name,
                    data_fn=self._make_audio_loader(un_name),
                    is_attended=False,
                    feature_name="audio",
                ),
            ]

            neural_fn = self._make_eeg_loader(dat_path)

            yield TrialRecord(
                subject=sub_id,
                session=1,
                trial=trial_idx,
                condition=condition,
                ns_type="eeg",
                stimulus=stimuli,
                neural_data_fn=neural_fn,
                structural_data_fn=None,
                behavioural_data_fn=None,
            )

    # ------------------------ lazy loaders ------------------------

    def _make_eeg_loader(self, dat_path: str) -> Callable[[], BaseRaw]:
        """
        Loader that:
          - reads Curry .dat (preload=False)
          - finds trigger onset/offset from first/last edge of 'Trigger'
          - extends offset by +10 s (heartbeat spacing)
          - crops and drops aux channels.
        """
        def _loader() -> BaseRaw:
            raw = read_raw_curry(dat_path, preload=False, verbose="ERROR")
            raw.rename_channels(lambda x: "PPO8" if x=="PPO8h" else x.replace("AFP", "AFp").replace("FP", "Fp"))
            raw.set_montage(self._make_mne_digmontage())

            # Trigger handling
            if "Trigger" not in raw.ch_names:
                raise RuntimeError(f"'Trigger' channel missing in {dat_path}")
            trig = raw.get_data(picks=["Trigger"]).ravel()
            fs = float(raw.info["sfreq"])
            edges = np.where(np.diff(trig) != 0)[0]
            if edges.size == 0:
                # fallback: no edges found
                return raw
            onset_idx = int(edges[0] + 1)
            offset_idx = int(edges[-1] + 1 + round(10.0 * fs))  # +10 s
            tmin = onset_idx / fs
            tmax = min(offset_idx / fs, (raw.n_times - 1) / fs)

            raw.drop_channels(["Trigger"])
            return raw.copy().crop(tmin=tmin, tmax=tmax)
        return _loader

    def _make_audio_loader(self, stem: str) -> Callable[[], Dict[str, Any]]:
        """
        Load '<stem>.wav' from stimuli/ ; returns {'fs': int, 'waveform': (1, T)}.
        """
        wav_path = os.path.join(self._audio_root, f"{stem}.wav")
        def _loader() -> Dict[str, Any]:
            if not os.path.exists(wav_path):
                raise FileNotFoundError(f"Audio not found: {wav_path}")
            fs, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]
            return {"fs": int(fs), "waveform": np.asarray(x, dtype=float)[None, :]}
        return _loader

    # ------------------------ helpers ------------------------

    def _discover_dat_files(self) -> List[str]:
        files: List[str] = []
        for i in range(30):
            files += glob.glob(os.path.join(self.root, f"S{i}", "*.dat"))
        # Also catch any files directly under root or different numbering
        files += glob.glob(os.path.join(self.root, "S*", "*.dat"))
        return sorted(set(files))

    def _parse_subject_and_cond(self, dat_path: str) -> Tuple[int, str]:
        """
        Filename convention: 'S<id>_<...>_<cond>.dat' where cond in {'1L','1R','2L','2R'}.
        """
        base = os.path.splitext(os.path.basename(dat_path))[0]
        parts = base.split("_")
        if len(parts) < 3:
            raise ValueError(f"Unexpected filename format for {base}")
        sub = int(parts[0].replace("S", ""))
        cond = parts[-1]
        if cond not in COND_MAP:
            raise ValueError(f"Unknown condition code '{cond}' in {base}")
        return sub, cond
    
    def _make_mne_digmontage(self,head_radius=0.095):
        path_to_ch_locs = os.path.join(self.root, "misc", "eeg255ch_locs.csv")
        ch_locs_df = pd.read_csv(path_to_ch_locs)
        fudicials_df = pd.DataFrame({
            "Name": ["Nasion", "Inion", "T9", "T10"],
            "Theta": [115, 115, -115, 115],
            "Phi": [90, -90, 0, 0],
            },
            index=["Nasion", "Inion", "T9", "T10"]
        )

        ch_locs_df["Cartesian"] = ch_locs_df.apply(lambda x: spherical_to_cartesian(head_radius, x['Theta'], x['Phi']), axis=1)
        fudicials_df["Cartesian"] = fudicials_df.apply(lambda x: spherical_to_cartesian(head_radius, x['Theta'], x['Phi']), axis=1)
        
        eeg_chs_df = df = ch_locs_df[~ch_locs_df["Channel Name"].isin(["XtraL", "XtraR"])]
        ch_cartesian = np.asarray(eeg_chs_df["Cartesian"].to_list())

        montage = make_dig_montage(
            ch_pos={eeg_chs_df.iloc[i]["Channel Name"]: ch_cartesian[i] for i in range(len(eeg_chs_df))},
            nasion=fudicials_df.loc['Nasion']['Cartesian'],
            lpa=fudicials_df.loc['T9']['Cartesian'],
            rpa=fudicials_df.loc['T10']['Cartesian']
        )
        return montage
                    

#### HANDLING MONTAGE ###

def spherical_to_cartesian(r, theta, phi):

    x = r * np.sin( 2*np.pi/360 * theta) * np.cos( 2*np.pi/360 * phi)
    y = r * np.sin( 2*np.pi/360 * theta) * np.sin( 2*np.pi/360 * phi)
    z = r * np.cos( 2*np.pi/360 * theta)

    return (x,y,z)


fudicials_df = pd.DataFrame({
    "Name": ["nasion", "inion", "left_preauricular", "right_preauricular"],
    "Theta": [115, 115, -115, 115],
    "Phi": [90, -90, 0, 0],
})

ADAPTOR = Narayanan2021Adapter