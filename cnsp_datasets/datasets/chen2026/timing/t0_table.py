"""Step 1: t0 of every chapter from the ROWS/ROWE trigger fit (../timing.py:t0_table), with the columns the later
steps read, plus each wav's duration and the EEG left after it.
usage: t0_table.py   -> <WORK>/t0_table.csv"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__)
import re  # noqa: E402

from scipy.io import wavfile  # noqa: E402

from cnsp_datasets.datasets.chen2026.timing import reader_of, t0_table  # noqa: E402

df = t0_table(settings.DOWNLOAD, settings.AUDIO)
df["run"] = df.file.map(lambda f: re.search(r"run-(\d+)", f).group(1))
df["wav_s"] = [len(wavfile.read(os.path.join(settings.AUDIO, f"{r.story}_{reader_of(r.sub)}", f"audio_{r.chapter}.wav"),
                                mmap=True)[1]) / 12000 for r in df.itertuples()]
df["margin_end_s"] = (df.file_s - df.t0_s - df.wav_s).round(1)
df["rows_found"] = df.rows_found.astype(str) + "/" + df.rows_json.astype(str)
df = df.rename(columns={"t0_s": "t0"}).round({"t0": 5, "res_sd_ms": 2})
os.makedirs(settings.WORK, exist_ok=True)
cols = ["sub", "story", "chapter", "file", "run", "t0", "drift_ppm", "res_sd_ms", "n_events", "rows_found", "wav_s",
        "file_s", "margin_end_s"]
df[cols].to_csv(os.path.join(settings.WORK, "t0_table.csv"), index=False)
print(f"{len(df)} chapters -> {os.path.join(settings.WORK, 't0_table.csv')}")
