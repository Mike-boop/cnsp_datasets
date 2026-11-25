"""
Paths of the chen2026 latency pipeline (README.md in this folder), from environment variables:
  CHEN2026_DOWNLOAD  chen2026 download dir (PassiveListening/ extracted), as given to the adaptor
  CHEN2026_AUDIO     the chen2026_audio repo (default: <download>/ChineseEEG-2_audio)
  CHEN2026_WORK      scratch dir for tables, caches, scans and figures (default: ./chen2026_timing_work)
  CHEN2026_DNN       accou2023 match-mismatch classifier (fs128_1020-64_broadband.pt)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[os.pardir] * 4))
DOWNLOAD = os.environ.get("CHEN2026_DOWNLOAD", "")
AUDIO = os.environ.get("CHEN2026_AUDIO") or os.path.join(DOWNLOAD, "ChineseEEG-2_audio")
WORK = os.environ.get("CHEN2026_WORK", "chen2026_timing_work")
ALIGN = os.path.join(WORK, "align")
MODEL = os.environ.get("CHEN2026_DNN", "")
TIMING_CSV = os.path.join(HERE, "timing.csv")
if REPO not in sys.path:
    sys.path.append(REPO)


def usage(doc: str, n_args: int = 0) -> None:
    """Print the script's docstring and the paths, and exit, for -h/--help or too few arguments."""
    if any(a in ("-h", "--help") for a in sys.argv[1:]) or len(sys.argv) - 1 < n_args:
        print(doc.strip())
        print(f"\npaths: DOWNLOAD={DOWNLOAD!r} AUDIO={AUDIO!r} WORK={WORK!r} MODEL={MODEL!r}")
        sys.exit(0)
