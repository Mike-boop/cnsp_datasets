"""Compact the polonenko2021 stimulus zips: keep only the keys the adaptor reads, in the original layout.

Usage: python -I compact_stimuli.py <zip> <out_root> <tmp_dir>
Writes <out_root>/<zip stem>/<original file name> as an expyfun hdf5 (expyfun/key_<name>) with the audio
variants, pulse_inds, fs and fc_band, so the adaptor reads it exactly like a full unzip. Resumable.
"""
import os
import sys
import zipfile

import h5py

KEYS = ("fs", "fc_band", "x", "x_play_single", "x_play_band")


def main(zpath, out_root, tmp_dir):
    os.makedirs(tmp_dir, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if not info.filename.endswith(".hdf5"):
                continue
            out = os.path.join(out_root, info.filename)
            if os.path.exists(out):
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            tmp = os.path.join(tmp_dir, os.path.basename(info.filename))
            with z.open(info) as src, open(tmp, "wb") as dst:
                while chunk := src.read(1 << 24):
                    dst.write(chunk)
            with h5py.File(tmp, "r") as f, h5py.File(out + ".part", "w") as g:
                e, o = f["expyfun"], g.create_group("expyfun")
                for k in KEYS:
                    e.copy(e["key_" + k], o)
                e.copy(e["key_pulse_inds"], o)
                for k, v in e.attrs.items():
                    o.attrs[k] = v
                for k, v in f.attrs.items():
                    g.attrs[k] = v
                g.attrs["compacted_from"] = info.filename
            os.replace(out + ".part", out)
            os.remove(tmp)
            print(out, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
