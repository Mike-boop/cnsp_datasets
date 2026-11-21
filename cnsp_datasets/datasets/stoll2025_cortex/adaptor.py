"""stoll2025, cortical montage (32 channels; exp1 1 kHz, exp2 500 Hz, native rates kept); see stoll2025/notes.md."""
from functools import partial

from cnsp_datasets.datasets.stoll2025.adaptor import Stoll2025Adaptor

ADAPTOR = partial(Stoll2025Adaptor, montage="cortex")
