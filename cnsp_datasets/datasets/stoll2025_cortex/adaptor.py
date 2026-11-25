"""stoll2025, cortical montage (32 channels; exp1 1 kHz, exp2 500 Hz, native rates kept); see stoll2025/notes.md."""
from cnsp_datasets.datasets.stoll2025.adaptor import Stoll2025Adaptor


class Stoll2025CortexAdaptor(Stoll2025Adaptor):
    """Stoll2025Adaptor with montage="cortex" (exp1 and exp2 only; exp3 has no cortical files)."""

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True,
                 save_anm: bool = False):
        super().__init__(download_dir, sfreq=sfreq, drift_correction=drift_correction, montage="cortex",
                         save_anm=save_anm)


ADAPTOR = Stoll2025CortexAdaptor
