"""Per-chapter analysis cache for the latency/drift scans (no data altered; analysis copies only).
For each t0_table row of one listener: read the chapter's BrainVision file (settings.DOWNLOAD), add VREF (Cz) as
zeros, set the GSN-HydroCel-129 montage, mark channels with SD > 5x or < 1/5 of the median SD (1-40 Hz) as bad
(analysis only), then save from sample floor(t0 * fs) on:
  eeg128: the fs128_1020-64 classifier input (0.5 Hz high-pass, 128 Hz, 64-ch 10-20 interpolation, average ref)
  env128: Hilbert envelope at 128 Hz (classifier stim steps), from audio sample 0
  eeg50 / env50: 129-ch (bads interpolated) average reference, 1-8 Hz, 50 Hz, |audio| envelope 1-8 Hz (as crossdec.py)
  te128 / te50: time (s, file clock) of EEG sample 0 at each rate; t0 from the trigger fit.
usage: prep_cache.py <sub>   (cache: <WORK>/align/cache/)"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import csv
import numpy as np
import mne, scipy.signal as ss, scipy.io.wavfile as wavfile
from cnsp_datasets.align.specs import load_classifier
from cnsp_datasets.preprocess.base import get_stim_array
mne.set_log_level('ERROR')
C, AUD, MODEL = settings.WORK, settings.AUDIO, settings.MODEL
_, spec, _ = load_classifier(MODEL)
steps = spec.eeg_steps()
filt, interp = steps[0], steps[2]      # high-pass 0.5 Hz, InterpolateToMontage; resampling done here first
sub = sys.argv[1]
rd = 'f1' if int(sub) <= 4 else 'm1'
out = f'{C}/align/cache'; os.makedirs(out, exist_ok=True)
b8 = ss.butter(2, [1, 8], 'bandpass', fs=50)
for r in csv.DictReader(open(f'{C}/t0_table.csv')):
    if r['sub'] != sub:
        continue
    st, k = r['story'], int(r['chapter'])
    path = f'{out}/sub-{sub}_{st}_ch{k:02d}.npz'
    if os.path.exists(path):
        continue
    raw = mne.io.read_raw_brainvision(os.path.join(settings.DOWNLOAD, 'PassiveListening', f'sub-{sub}', f'ses-{st}', 'eeg',
                                                   r['file']), preload=True)
    raw = mne.add_reference_channels(raw, 'Cz')
    raw.set_montage('GSN-HydroCel-129')
    fs0 = raw.info['sfreq']; t0 = float(r['t0'])
    x = raw.get_data(picks='eeg')
    sos = ss.butter(4, [1, 40], 'bandpass', fs=fs0, output='sos')
    lsd = np.log(ss.sosfiltfilt(sos, x[:, ::1], axis=1).std(1) + 1e-12)
    zz = lsd - np.median(lsd[:-1])  # VREF (zeros) excluded from the median
    bads = [raw.ch_names[i] for i in np.flatnonzero(np.abs(zz) > np.log(5)) if raw.ch_names[i] != 'Cz']
    raw.info['bads'] = bads
    # 50 Hz decoder input (all 129 channels, average reference over good ones)
    r50 = raw.copy()
    if bads:
        r50.interpolate_bads(reset_bads=True)  # same 129 channels in every chapter (decoder trained across chapters)
    r50.set_eeg_reference('average')
    x50 = ss.resample_poly(r50.get_data(picks='eeg'), 50, int(fs0), axis=1)
    x50 = ss.filtfilt(*b8, x50, axis=1)
    i50 = int(np.floor(t0 * 50)); eeg50 = x50[:, i50:].astype(np.float32); del r50, x50
    # classifier input
    raw = filt.run(raw)
    raw.resample(128, npad='auto', window='hann')
    raw = interp.run(raw)
    x128 = raw.get_data()
    i128 = int(np.floor(t0 * 128)); eeg128 = x128[:, i128:].astype(np.float32)
    sr, au = wavfile.read(f'{AUD}/{st}_{rd}/audio_{k}.wav')
    a = au.astype(float).mean(1)
    d = {'fs': sr, 'data': a[None]}
    for s_ in spec.stim_steps():
        d = s_.run(d)
    env128 = np.atleast_2d(get_stim_array(d)).astype(np.float32)
    env50 = ss.filtfilt(*b8, ss.resample_poly(np.abs(a), 1, sr // 50)).astype(np.float32)
    np.savez(path, eeg128=eeg128, env128=env128, eeg50=eeg50, env50=env50, t0=t0, te128=i128 / 128, te50=i50 / 50,
             bads=np.array(bads), wav_s=len(a) / sr)
    print(f'sub-{sub} {st} ch{k:02d}: bads {bads} eeg {eeg128.shape[1] / 128:.0f}s wav {len(a) / sr:.0f}s', flush=True)
