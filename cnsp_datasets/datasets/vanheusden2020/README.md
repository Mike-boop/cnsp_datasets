# vanheusden2020: hearing-impaired listeners hear an audiobook with and without their hearing aids (English, EEG)

EEG while 20 adults with mild-to-moderate hearing loss, all hearing-aid users, listen to 8 audiobook segments
(141-240 s each). The audiobook is *The Children of Odin* (Padraic Colum, LibriVox, female reader). It is played
from a loudspeaker 1.2 m in front of the listener at 70 dBA. Each subject hears the same 8 segments twice: once
wearing their own hearing aids (`aided`) and once without (`unaided`). There is one recording per condition, and
the condition order varies between subjects. English.

> **Cortical tier plus a population-level middle-latency response.** The `low` and `mlr` tiers pass in both
> conditions. The brainstem tier fails. Triggers mark the segment onsets only. The trigger type is unknown and
> there is no stimtrack, so drift cannot be measured. The EEG is stored **with its original BioSemi CMS/DRL
> reference: re-reference before use.** In the `aided` condition the sound reached the ear through each
> participant's hearing aid. That processing (gain, compression, delay) is not shipped.

- **Source:** University of Southampton ePrints, Vanheusden FJ et al. (2019). *Dataset for: Hearing aids do not
  alter cortical entrainment to speech at audible levels in mild-to-moderately hearing-impaired subjects.*
  doi:10.5258/SOTON/D1140 (ePrints 438737). **Licence: CC BY 4.0** (ePrints record; the shipped readme says
  "CC-BY"). Derived data may be redistributed with attribution.
- **Paper:** Vanheusden FJ, Kegler M, Ireland K, Georga C, Simpson DM, Reichenbach T, Bell SL (2020). Hearing aids
  do not alter cortical entrainment to speech at audible levels in mild-to-moderately hearing-impaired subjects.
  *Front. Hum. Neurosci.* 14:109. doi:10.3389/fnhum.2020.00109
- **Code (authors):** none shared.

## Size
**20 participants, 308 trials, 16.14 h in total, 0.807 h (48.4 min) per participant (range 0.339-0.845 h).**
- `aided`: 155 trials, 8.13 h, 0.407 h per participant (0.169-0.423);
- `unaided`: 153 trials, 8.01 h, 0.400 h per participant (0.169-0.423).

A full block is 8 segments (1521.5 s = 25.4 min). The shorter participants are:
- S_002: chapter 1 only (4 segments, 609.7 s) in each condition.
- S_004 `unaided` and S_020 `aided`: no `odin_4_4`.
- S_019 `unaided`: no `odin_4_3` or `odin_4_4`.

These hours are computed from the stimulus durations. The 40 BDF recordings, including breaks and questions, total
21.4 h.

## What is provided
- **EEG:** BioSemi ActiveTwo, 32 scalp channels. Recorded at 2048 Hz, DC-coupled, with the BioSemi 417 Hz
  decimation low-pass. Stored at **1024 Hz** (decimated by 2 with an anti-alias FIR), in V.
  - **Reference: CMS/DRL as recorded** (reference-free). The data are not re-referenced. The paper used the
    average reference, and so does the validation below.
  - Channels are renamed from the BioSemi `A1-A32` labels to the `biosemi32` template (Fp1 ... Cz), and the
    positions are **template positions**. Neither the label mapping nor the positions are documented: they are
    inferred from neighbour correlations. There is no digitisation.
- **External sensors:** `EXG1` and `EXG2` are the mastoids, stored as `misc` under their own names. The paper
  says only "either mastoid". The sides are **inferred: EXG1 = right, EXG2 = left**. This is the reverse of the
  usual BioSemi convention. The inference comes from EXG1 correlating more with T8 and EXG2 more with T7, in 35 of
  40 files. Use them for a linked-mastoid reference if wanted.
- **Dropped:** `EXG3`, which is active but has an unknown role (EOG? nose?). Also `EXG4-8` (unconnected), the
  `GSR`/`Erg`/`Resp`/`Plet`/`Temp` channels (constant) and `Status`. **No EOG or ECG** channel is identified, and
  there is no stimtrack or audio channel.
- **Stimulus** per trial: `odin_1_1 ... odin_1_4`, `odin_4_1 ... odin_4_4`, feature `audio`. These are the
  shipped wavs: 44.1 kHz, mono, unchanged. The same wav is used for both conditions.
  - The wavs are **band-limited at ~4.05 kHz**, but the paper says it low-pass filtered at 3 kHz. They may
    therefore not be exactly what was played.
  - `odin_4_*` is ~10 dB lower in RMS than `odin_1_*`, but all segments were presented at 70 dBA. The
    calibration is not shipped.
  - No envelope, no transcript and no word or phoneme timings are provided. The comprehension questionnaire is in
    the download, but the per-segment answers are not.
- **Trials and sessions:** trials are numbered over both recordings of a subject in recording order (BDF
  `meas_date`). Session = recording day. S_017, S_020 and S_024 recorded the two conditions on different days, so
  their second recording is **session 2**. The readme says "same day". All other subjects have session 1 only.
- **Trial metadata** (`raw.info["description"]`, JSON): `wav`, `bdf`, `slot_in_recording`, `onset_sample_2048`,
  `recording_rank`, `meas_date`, `order_source` (`fixed` / `eeg`), `order_ambiguous`, `missing_segments`,
  `paper_id_inferred`, `excluded_in_paper`, `reference`, `external_sensors`, `dropped`, `units_as_shipped`,
  `positions`, `n_samples`, `n_samples_stimulus`, `eeg_shorter_than_stimulus`.
- **Not exported:** the BKB sentence test from the paper, which is not in the dataset (no audio, no EEG). Also not
  exported are 120 unexplained 1-s pulses after the audiobook in S_027 `aided`, and the behavioural xlsx
  (audiometry, hearing-aid fittings, questionnaire), which is in the download.

## Alignment
- **Onset only (`onset_only`).** Each trial starts at the rising edge of Status bit 1 (value 2), which marks each
  segment onset, and lasts as long as the wav. There is no offset trigger. The code does not identify the segment.
- **Segment order: inferred, not documented.** Segments are assumed to play in the fixed order `1_1, 1_2, 1_3,
  1_4, 4_1, 4_2, 4_3, 4_4` in both conditions. This is based on:
  - Trigger gaps: in every file, each gap is longer than the wav at that position.
  - A leave-one-subject-out EEG test: the fixed order is the best feasible order in 31 of 35 eight-segment files.
    The 4 exceptions (S_004 `aided`, S_008 `aided`, S_011 `aided`, S_017 `unaided`) are among the weakest files,
    and their best orders disagree with each other.
  - **S_002 `unaided`** is the one exception, with order `1_3, 1_4, 1_1, 1_2` taken from the EEG
    (`order_source = "eeg"`).
  - Weak or ambiguous files are flagged with `order_ambiguous`: S_004 (both files), S_008 `aided`, S_011 `aided`,
    S_017 `unaided`, and slots 2 and 5 of S_019 `unaided`.
- **Trigger type: unknown.** The paper and readme say nothing about how triggers were generated. The pulse width
  varies by 3 samples. Absolute trigger-to-sound latency is unknown. The loudspeaker distance alone adds 3.5 ms.
  The hearing-aid delay in `aided` is unknown.
- **Drift: not estimable.** There are onset triggers only, separated by breaks of variable length. The one hint
  is the 1-s pulse train in S_027 `aided`, which runs at -24 ppm against the EEG clock (<= ~6 ms over a 240 s
  segment). It is unknown whether the audio used the same clock. No correction is applied.
- **Jitter:** the per-trial offset from the validator has a MAD of 13 ms (aided 13.1, unaided 15.0). This is at
  the resolution of a cortical (64 Hz) estimate, so it is an upper bound rather than a measured trigger jitter. The
  trigger jitter itself is unknown.
- **Constant offset (documented, not applied):** a match-mismatch DNN trained on accou2023 places this EEG
  **~5 ms early relative to accou2023**: `aided` +4.4 ms (95% CI +0.7 to +7.2) and `unaided` +5.1 ms (+1.5 to
  +8.3), on 100 trials per condition. "Early" suggests the trigger fires a few ms after the actual sound onset.
  This is unverified, and the loudspeaker distance cannot explain it, because distance would make the EEG late.
  Following the project rule, the shift is not applied.

## Validation
**`mlr` tier, pooled and in each condition.** The brainstem tier was run and fails. Settings: repo validator,
forward model, 32 scalp channels, average reference.
- **low (0.5-8 Hz, 64 Hz):** mean r **0.058** (median 0.054, range 0.033-0.092). **20/20** subjects pass pooled;
  `aided` 18/20 (r 0.057) and `unaided` 19/20 (r 0.057). The subject-level misses are S_004 `aided` (r 0.025,
  p_circ 0.059) and S_014 in both conditions separately (S_014 passes pooled). S_014 has large artifacts.
- **mlr (30-60 Hz, 18-45 ms):** mean SNR **1.46** pooled (12/20 subjects), 1.25 `aided` (6/20), 1.33 `unaided`
  (9/20). Population p = 0.0099 (the permutation floor) in all three. The GFP peaks at 40-43 ms, near the upper
  edge of the window.
- **brainstem (30-250 Hz, 4-9 ms):** fails. SNR 0.99 pooled (p 0.45), 0.94 `aided`, 0.97 `unaided`, with 1/20
  subjects significant (chance level).
- **Forward TRF** (0.5-8 Hz, GFP): the main peak is at **172 ms** in both conditions. There is a secondary bump
  near 0 ms, at about half the main peak (GFP ratio median 0.51, > 0.3 in 18/20 subjects). It is **not a timing
  problem**:
  - Envelope autocorrelation does not explain it: a synthetic control built from the 100-300 ms TRF gives a ratio
    of 0.03.
  - Its topography matches the 172 ms peak (grand-map r 0.98), with no ocular pattern.
  - The hand-aligned reference datasets show the same ratio (weissbart2019 0.69, fuglsang2018 0.62,
    bentum2023 0.49).
- **Order-ambiguous trials** score lower (median r 0.034, n 41, vs 0.058, n 267). This is expected, because those
  files were flagged for weak tracking. S_002 `unaided`, with its EEG-derived order, scores r 0.102. That result
  is partly circular, because the order was chosen on the EEG.
- **Aided vs unaided:** there is no measurable difference in r (p 0.70), TRF latency, per-trial offset (-1.4 ms,
  SEM 1.4) or MLR SNR. A hearing-aid delay of a few ms cannot be resolved at this resolution.
- **S_014 `aided` trial 9** has a -19.5 s offset in the validator output. This is an **estimator artefact**: an
  unbounded parabolic step in `models.peak_shift` at the search edge. It is not a misalignment. A ±30 s sweep finds
  no tracking at any lag. This trial inflates the aided jitter SD to 1562 ms, so use the MAD.
- **Coherence** (EEG-envelope, complex mean over subjects, average reference, 5 s Hann windows with 4 s overlap,
  ratio to a surrogate):

  | condition (trials) | rate | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz | 30-60 Hz |
  |---|---|---|---|---|---|---|---|
  | `aided` (155) | 128 Hz | 6.3 | 6.9 | 6.3 | 1.87 | 1.19 | 1.06 |
  | `unaided` (153) | 128 Hz | 6.1 | 6.5 | 5.4 | 1.77 | 1.14 | 1.18 |
  | `aided` | native 1024 Hz | 6.3 | 6.9 | 6.4 | 1.86 | 1.19 | 1.12 |
  | `unaided` | native 1024 Hz | 6.1 | 6.4 | 5.4 | 1.77 | 1.14 | 1.19 |

  At native rate the 60-120, 120-250 and 250-500 Hz bands are all 0.99-1.03.
- **Suitable for:**
  - low-frequency envelope tracking and decoding, and cortical TRFs;
  - aided vs unaided comparisons of cortical tracking in hearing-impaired listeners;
  - population-level middle-latency (30-60 Hz) responses.
- **Not suitable for:**
  - brainstem responses (no response found; free-field loudspeaker; trigger type and latency unknown; ~4 kHz
    band-limited audio; unknown hearing-aid processing in `aided`);
  - latency comparisons at the few-ms level, including hearing-aid delay (unknown audio latency, ~5 ms DNN offset,
    13 ms per-trial MAD);
  - individual-subject middle-latency analyses;
  - models of the sound at the eardrum in `aided`;
  - analyses that need measured electrode positions or EOG.

## Caveats
- **Re-reference before use.** The EEG has the BioSemi CMS/DRL reference as recorded. Use the average reference
  (as the paper did) or the mastoids `EXG1`/`EXG2`. The mastoid sides are inferred.
- **Subjects vs the paper.** The paper has 17 subjects. The release has 20. S_002, S_019 and S_020 are not in the
  paper. The paper removed its subject 13 from the EEG analysis for a "technical issue". By an age/gender match,
  that subject is **S_016** (inferred; see `paper_id_inferred` and `excluded_in_paper`). S_016 is kept here because
  its tracking is normal. Exclude it to reproduce the paper.
- **Stimulus as played:** the wavs are band-limited at ~4.05 kHz, but the paper says 3 kHz. The chapter levels
  differ, with no calibration shipped. The hearing-aid processing in `aided` is not shipped and cannot be
  reconstructed.
- **Segment order is inferred** (see Alignment). Check `order_source` and `order_ambiguous`, and consider
  excluding the ambiguous files.
- **Missing segments** (no trigger, no evidence they were played): S_004 `unaided` and S_020 `aided` lack
  `odin_4_4`, and S_019 `unaided` lacks `odin_4_3` and `odin_4_4`. These are listed in `missing_segments`. S_002
  has chapter 1 only. Its files are called `..._Speech_Rep.bdf`, and "Rep" is unexplained.
- **Session 2** for S_017, S_020 and S_024 (conditions recorded on different days).
- Large transient artifacts in S_007 `unaided`, S_014 `unaided` and S_016 `aided`. No channels are marked bad.
- Upstream issues:
  - The readme says 17 subjects and "same day" recording.
  - The segment order and trigger scheme are undocumented.
  - The loose `S_001_Unaided_Speech_Deci.bdf` duplicates the zipped file.
  - The paper's 3 kHz filter does not match the shipped wavs.
  - The BKB data and per-segment comprehension scores are not shipped.

Details: `notes.md`.
