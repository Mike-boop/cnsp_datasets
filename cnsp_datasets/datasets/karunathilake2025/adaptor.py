from __future__ import annotations

import glob
import os
from typing import Callable, Iterable

import mne

from cnsp_datasets.datasets.simon_base.common import (REFERENCE, audio_loader, check_unique_subjects, crop_meg,
                                                      find_one, read_raw, rms_bads, stim_events, subject_number,
                                                      wav_samples)
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1000
AUDIO_FS = 22050
# Trigger code -> stimulus (exp.py ACOUSTICS, PHONEMES, LEXICAL, SEMANTIC); 177 is not used.
CODES = {164: "ASN_M01", 165: "ASN_M02", 166: "ASN_M03", 167: "ASN_M04", 168: "PH_M01", 169: "PH_M02",
         170: "PH_M03", 171: "PH_M04", 172: "ASM_M01", 173: "ASM_M02", 174: "ASM_M03", 175: "ASM_M04",
         176: "AS_M01", 178: "AS_M02", 179: "AS_M03", 180: "AS_M04"}
# Passage-type prefix -> condition (exp.py epoch names).
CONDITIONS = {"ASN": "noise", "PH": "nonwords", "ASM": "scrambled", "AS": "narrative"}
FLAT_RATIO = 20  # channel rms below median / 20 in 10 x 10 s windows -> bad (flat; notes.md section 5)
SATURATED_RATIO = 30  # ... or above 30 x median -> bad (R2682 MEG 086 jumps between the rails, 88 x median)
TRIGGER_TYPE = ("software (inferred: TTL codes from the stimulus PC, recorded on MISC 009 and STI 014; latency "
                "to sound onset and tube delay unknown, no audio channel)")
NOTES = ("Onset = trigger (one TTL code per passage onset, no offset codes), no shift and no drift correction (no "
         "audio channel and no offset triggers: drift not measurable; ~1-3 ms over a 62 s trial for typical "
         "clocks). Trial length = played wav. Units T. MEG 001-157 axial gradiometers (MNE type mag) + 3 reference "
         "magnetometers; MISC lines (TTL trigger lines, idle or noise-only ports) and STI 014 dropped. Flat and "
         "saturated channels in info['bads']. Each passage is played twice in a row; gTTS speech.")


class Karunathilake2025Adaptor:
    """
    Speech-modulated noise, nonwords, scrambled words and narrative passages (Karunathilake, Brodbeck, Bhattasali,
    Resnik & Simon 2025, J Neurosci; Dryad doi:10.5061/dryad.ht76hdrpf): KIT 157-channel MEG at 1 kHz, one
    recording per participant, 16 synthesised 1-min passages each played twice in a row (32 trials, presentation
    order). Subject = full R-number (R2383 -> 2383; R-number in the sidecar). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(find_one(os.path.join(self.root, "**/AS_M01.wav")))
        paths = sorted(glob.glob(os.path.join(self.root, "**", "R*", "R*_fif-raw.fif"), recursive=True))
        pids = [os.path.basename(p).split("_")[0] for p in paths]
        check_unique_subjects(pids)
        for path, pid in zip(paths, pids):
            raw = read_raw(path, FS)
            events = stim_events(raw, CODES)
            if (len(events) != 2 * len(CODES) or any((events[:, 2] == c).sum() != 2 for c in CODES)
                    or (events[0::2, 2] != events[1::2, 2]).any()):
                raise ValueError(f"{path}: expected each of {len(CODES)} codes twice in a row, got "
                                 f"{events[:, 2].tolist()}")
            count = dict.fromkeys(CODES, 0)
            for trial, (sample, code) in enumerate(events[:, [0, 2]].tolist(), 1):
                count[code] += 1
                name = CODES[code]
                prefix, passage = name.split("_M")
                onset = sample - raw.first_samp
                description = provenance(
                    "sw_trigger", TRIGGER_TYPE, NOTES, participant=pid, passage_type=CONDITIONS[prefix],
                    passage=int(passage), repetition=count[code], block=(trial - 1) // 8 + 1, trigger_code=code,
                    onset_s=onset / FS, stimulus_file=f"{name}.wav", units_as_shipped="T", reference=REFERENCE)
                wav = os.path.join(stim_dir, f"{name}.wav")
                yield TrialRecord(
                    subject=subject_number(pid), session=1, trial=trial, condition=CONDITIONS[prefix],
                    ns_type="meg",
                    stimulus=[StimulusRecord("audio", name, audio_loader(wav, AUDIO_FS), is_attended=True)],
                    neural_data_fn=_meg_loader(path, onset, wav_samples(wav, AUDIO_FS, FS), description),
                )


def _meg_loader(path: str, onset: int, n_out: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    """Trial from the onset trigger (opening R####_fif-raw.fif joins the -1 split where there is one); flat and
    saturated gradiometers as bads."""
    def _loader():
        return crop_meg(read_raw(path, FS), onset, n_out, description,
                        rms_bads(path, FS, FLAT_RATIO, SATURATED_RATIO))

    return _loader


ADAPTOR = Karunathilake2025Adaptor
