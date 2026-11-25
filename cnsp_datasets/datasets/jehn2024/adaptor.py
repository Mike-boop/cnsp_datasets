import os

from cnsp_datasets.datasets.jehn2025_base.adaptor import Jehn2025Adaptor


class Jehn2024Adaptor(Jehn2025Adaptor):
    """
    Jehn et al. 2024 (Zenodo 10980117): one HDF5 archive at 125 Hz (file name: 1-32 Hz, ICA) in the layout of the
    Jehn 2025 archives, read by the jehn2025 adaptor with these constants. Behaviour as before the restructure
    (except the changes listed in notes.md): the plain parity rule for the attended side (no SWAPPED_SIDES; the
    swaps were found on the jehn2025 1 kHz data and are not checked here), stimulus names without the
    _target/_distractor suffix, no drift correction.
    """

    H5_FNAME = "ci_attention_final_l_1,1_h_32,50_out_125_130_incl_ica.hdf5"
    SWAPPED_SIDES = set()
    NAME_SUFFIX = {"attended": "", "distractor": ""}
    FS_EEG = 125
    FS_ENV = 125
    INFO_FIF_PATH = os.path.join(os.path.dirname(__file__), "info_125.fif")

    def __init__(self, download_dir: str):
        super().__init__(download_dir, h5_fname=self.H5_FNAME)


ADAPTOR = Jehn2024Adaptor
