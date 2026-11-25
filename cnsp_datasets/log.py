"""
Logging for standardisation runs.

Modules log through `logging.getLogger(__name__)`; `standardise_log(out_dir)` adds a handler that writes everything
from the cnsp_datasets package to <out_dir>/standardise.log (warnings, e.g. a recording that ends before its
trial, and the traceback of every trial that failed). MNE's own verbosity is left to the user: set the
environment variable MNE_LOGGING_LEVEL (e.g. "WARNING") or call mne.set_log_level; adaptors must not change it.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

PACKAGE = "cnsp_datasets"
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


@contextmanager
def standardise_log(out_dir: str | Path, level: int = logging.INFO):
    """Write the package's log records to <out_dir>/standardise.log (appending) while the block runs."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(out_dir / "standardise.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.setLevel(level)
    logger = logging.getLogger(PACKAGE)
    previous = logger.level
    logger.addHandler(handler)
    if logger.level == logging.NOTSET or logger.level > level:
        logger.setLevel(level)
    try:
        yield out_dir / "standardise.log"
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
        handler.close()
