import numpy as np
from scipy.signal import hilbert, resample_poly
from scipy.fft import rfft, irfft, next_fast_len

from cnsp_datasets.preprocess.base import StimulusPreprocStep, StimulusData, get_stim_array


class HilbertEnvelope(StimulusPreprocStep):
    """
    Extracts the amplitude envelope of a stimulus via the Hilbert transform.

    output_feature_name defaults to "envelope", so applying this step to an
    "audio" stimulus will replace it with feature_name="envelope".
    """

    def __init__(self, output_feature_name: str = "envelope"):
        self.output_feature_name = output_feature_name

    def run(self, data: StimulusData) -> StimulusData:
        envelope = np.abs(hilbert(get_stim_array(data), axis=-1))
        return {"fs": data["fs"], "data": envelope}


# --- ERB helpers (Slaney) ---
def _hz_to_erb_rate(f):
    return 21.4 * np.log10(4.37e-3 * f + 1.0)


def _erb_rate_to_hz(er):
    return (10 ** (er / 21.4) - 1.0) / 4.37e-3


def _erb_width(f):
    return 24.7 * (4.37e-3 * f + 1.0)


def _crop_convolution(full: np.ndarray, n1: int, n2: int, mode: str) -> np.ndarray:
    """Crop a 'full' linear convolution (length n1+n2-1) to the requested mode."""
    if mode == "full":
        return full
    elif mode == "same":
        start = (n2 - 1) // 2
        return full[..., start:start + n1]
    elif mode == "valid":
        valid_len = max(n1, n2) - min(n1, n2) + 1
        start = min(n1, n2) - 1
        return full[..., start:start + valid_len]
    else:
        raise ValueError("mode must be 'full', 'same', or 'valid'.")


class GammatoneEnvelope(StimulusPreprocStep):
    """
    Extracts per-channel amplitude envelopes from a gammatone filterbank.

    Filters the stimulus with a bank of ERB-rate spaced gammatone filters,
    half-wave rectifies and compresses each subband, then resamples to
    target_fs. Replaces the (1, time) input with an (n_channels, time) array.

    output_feature_name defaults to "gammatone_envelope", so applying this
    step to an "audio" stimulus will replace it with
    feature_name="gammatone_envelope".

    Convolution is done by taking a single rfft of the (long) stimulus and
    reusing it for every channel, rather than recomputing it once per
    channel as a naive per-channel fftconvolve loop would — ~10x faster in
    practice. `workers` controls how many threads scipy.fft may use for
    that shared FFT/inverse-FFT; keep it at 1 (default) when records are
    already parallelized across processes (e.g. preprocess_dataset's
    n_jobs > 1) to avoid oversubscribing CPUs, and raise it (e.g. -1 for
    all cores) when processing one record at a time.

    Channels are processed in batches of `channel_batch_size` so that only
    that many channels' worth of (n_samples,)-sized FFT buffers are held in
    memory at once (the shared rfft of the stimulus itself is still only
    computed once, regardless of batch size). Materializing all channels'
    spectra at once (channel_batch_size=None) uses O(n_channels * n_samples)
    memory, which for multi-minute audio can reach tens of GB per call —
    batching trades a small amount of speed for a bounded memory footprint.
    """

    def __init__(
        self,
        target_fs: int,
        n_channels: int = 64,
        f_min: float = 50.0,
        f_max: float | None = 8000,
        order: int = 4,
        ir_duration: float = 0.100,
        mode: str = "same",
        normalize: str = "peak",
        compression: float = 0.6,
        dtype: type = np.float32,
        workers: int = 1,
        channel_batch_size: int | None = 8,
        output_feature_name: str = "gammatone_envelope",
    ):
        self.target_fs = target_fs
        self.n_channels = n_channels
        self.f_min = f_min
        self.f_max = f_max
        self.order = order
        self.ir_duration = ir_duration
        self.mode = mode
        self.normalize = normalize
        self.compression = compression
        self.dtype = dtype
        self.workers = workers
        self.channel_batch_size = channel_batch_size
        self.output_feature_name = output_feature_name

    @staticmethod
    def get_center_freqs(n_channels: int, f_min: float, f_max: float | None) -> np.ndarray:
        """Return the center frequencies of a gammatone filterbank."""
        f_max = f_max if f_max is not None else 0.95 * (44100 / 2.0)
        er_lo = _hz_to_erb_rate(f_min)
        er_hi = _hz_to_erb_rate(f_max)
        erb_rates = np.linspace(er_lo, er_hi, n_channels)
        return _erb_rate_to_hz(erb_rates)

    def run(self, data: StimulusData) -> StimulusData:
        x = np.asarray(get_stim_array(data), dtype=self.dtype).squeeze()
        if x.ndim != 1:
            raise ValueError("GammatoneEnvelope expects a mono stimulus.")

        sr = data["fs"]
        f_max = self.f_max if self.f_max is not None else 0.95 * (sr / 2.0)

        # Center frequencies spaced uniformly in ERB-rate
        er_lo = _hz_to_erb_rate(self.f_min)
        er_hi = _hz_to_erb_rate(f_max)
        erb_rates = np.linspace(er_lo, er_hi, self.n_channels)
        center_freqs = _erb_rate_to_hz(erb_rates).astype(self.dtype)

        # Time axis for impulse response
        ir_len = int(np.round(self.ir_duration * sr))
        if ir_len < 2:
            raise ValueError("ir_duration is too short for the given sample rate.")
        t = (np.arange(ir_len) / sr).astype(self.dtype)

        # Build all filters at once (real bandpass using cosine carrier):
        # h(t) = t^(order-1) * exp(-2π*b*t) * cos(2π*f_c*t), b = 1.019 * ERB(f_c)
        b = (1.019 * _erb_width(center_freqs))[:, None]
        fc = center_freqs[:, None]
        env = (t[None, :] ** (self.order - 1)) * np.exp(-2.0 * np.pi * b * t[None, :])
        h = (env * np.cos(2.0 * np.pi * fc * t[None, :])).astype(self.dtype)

        if self.normalize == "l2":
            h = h / (np.linalg.norm(h, axis=1, keepdims=True) + 1e-12)
        elif self.normalize == "peak":
            h = h / (np.max(np.abs(h), axis=1, keepdims=True) + 1e-12)
        else:
            raise ValueError("normalize must be 'peak' or 'l2'.")

        # rfft the stimulus once and reuse it for every channel instead of
        # recomputing it per channel (see docstring). Channels are processed
        # in batches so we don't hold all n_channels FFT buffers at once.
        n1, n2 = x.shape[-1], h.shape[-1]
        nfft = next_fast_len(n1 + n2 - 1)
        X = rfft(x, nfft, workers=self.workers)

        out_len = {
            "full": n1 + n2 - 1,
            "same": n1,
            "valid": max(n1, n2) - min(n1, n2) + 1,
        }.get(self.mode)
        if out_len is None:
            raise ValueError("mode must be 'full', 'same', or 'valid'.")

        batch_size = self.channel_batch_size or self.n_channels
        subbands = np.empty((self.n_channels, out_len), dtype=self.dtype)
        for start in range(0, self.n_channels, batch_size):
            h_batch = h[start:start + batch_size]
            H = rfft(h_batch, nfft, axis=-1, workers=self.workers)
            full = irfft(X[None, :] * H, nfft, axis=-1, workers=self.workers)[:, : n1 + n2 - 1]
            subbands[start:start + batch_size] = _crop_convolution(full, n1, n2, self.mode)

        subbands[subbands < 0] = 0
        subbands = np.power(subbands, self.compression)

        envelope = resample_poly(subbands, self.target_fs, sr, axis=-1)
        return {"fs": self.target_fs, "data": envelope}

