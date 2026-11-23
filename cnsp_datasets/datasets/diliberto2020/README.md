# diliberto2020: monophonic Bach melodies on piano (EEG)

EEG of 20 listeners, 1-10 non-musicians and 11-20 expert pianists. They listened to 10 monophonic Bach pieces,
synthesised from MIDI with MuseScore 2 piano sounds (~2.7 min each). Each piece was played 3 times in random order:
30 trials per listener.

- **Source:** Dryad doi:10.5061/dryad.g1jwstqmh (registry entry `diliberto2020`), CND files, 5.98 GB.
  - The played wavs are **not on Dryad**. They come from the Kern et al. (2022) Donders collection
    DSC_3018045.02_116_v1, doi:10.34973/5qxw-nn97 (registry entry `diliberto2020_audio`: only the 10 wavs, 278 MB).
- **Licence:** EEG **CC0 1.0** (Dryad). The wavs are **CC BY 4.0 plus the Radboud data use agreement**; they need a
  data.ru.nl account.
- **Paper:** Di Liberto GM, Pelofi C, Bianco R, Patel P, Mehta AD, Herrero JL, de Cheveigné A, Shamma S,
  Mesgarani N (2020). Cortical encoding of melodic expectations in human temporal cortex. *eLife* 9:e51784.
  doi:10.7554/eLife.51784. The ECoG patients of the paper are not in the release.
- **Code (authors):** none shared.

## Size
**20 participants x 1.335 h = 26.7 h** (80.1 min each, the same for everyone). Musicians and non-musicians have
13.3 h each, and there is one condition, `listening`.
- Durations come from the stimuli (`notes.md` section 8). `validation.json` gives the same totals.
- There are 26.7 min of unique audio.
- The standardised output is about 13 GB.

## What is provided
- **EEG:** BioSemi ActiveTwo, 64 scalp channels (biosemi64 template positions), **512 Hz native, stored at
  512 Hz**.
  - The data are raw: no filter and no reference (CMS/DRL).
  - **Units:** the values were shipped as BioSemi ADC counts and are scaled by 31.25 nV to V. The scale factor is
    inferred (integer values, plausible µV after scaling); the readme does not state units.
  - **Mastoids:** `M1`/`M2` (`misc`). There are no EOG, stimulus or trigger channels.
- **Bad channels:** sub8 C4 and sub12 Fpz (noise without EEG) are listed in `info['bads']`. `raw.pick("eeg")` keeps
  bads; exclude them yourself.
- **Stimuli:** by default (`stimulus="audio"`) the played wav of each piece, `piece01`-`piece10` (44.1 kHz stereo,
  L and R near-identical, as shipped).
  - **Envelope option:** `stimulus="envelope"` uses the authors' 64 Hz envelope from Dryad instead.
  - **Note features:** `note_features=True` adds the shipped note-onset and pitch-weighted note-onset vectors, which
    are derived from the score.
  - The MIDI scores are downloaded but not used. The IDyOM expectation features are not shipped.
- **Trials:** trial = shipped index + 1. The presentation order is not shipped (`origTrialPosition` is empty), and
  "repetition" is the authors' label.

## Alignment
- **Trials were cut by the authors.** The readme puts the stimulus onset at EEG sample 513 (`paddingStartSample`
  + 1). The adaptor drops the 512 leading samples and keeps the ~1 s of EEG after the stimulus.
- **Trigger:** the triggers were not shared, and their route is unknown (Presentation software; Sennheiser HD650,
  so there is no tube delay).
- **Wav timing:** the wavs match the shipped envelope at lag 0 (r 0.9995-0.9999, exact lengths), so the onset
  applies to them.
- **Drift and jitter:** they cannot be estimated, because the trial lengths were set by the authors.
- **Alignment grade: medium.** Authors' epochs, with the onset at sample 513 per the readme (trigger unknown). The
  wavs match the shipped envelope at lag 0. The 30-60 Hz TRF peaks at 22-47 ms, with nothing at negative lags. mlr
  tier.

## Download and adaptor options
- **EEG:** `download_dataset("diliberto2020", <dir>)`. Dryad needs a token. Put Dryad API client credentials in
  `secrets.json` (`dryad-client-id`, `dryad-client-secret`) and export them as `DRYAD_CLIENT_ID` /
  `DRYAD_CLIENT_SECRET`. Alternatively, export a short-lived token (`dryad`) as `DRYAD_TOKEN`.
- **Audio:** `download_dataset("diliberto2020_audio", <dir>/donders)`. This needs the data.ru.nl WebDAV credentials
  (`secrets.json` keys `ru-rdr-usr` / `ru-rdr-pwd`) exported as `RADBOUD_USERNAME` / `RADBOUD_PASSWORD`. It is the
  default stimulus: the adaptor stops if the wavs are missing, unless `stimulus="envelope"`.
- `DiLiberto2020Adaptor(download_dir, stimulus="audio", note_features=False)`. With `format_dataset`, pass these as
  `--adaptor-opt key=value`.
- **Acknowledge** the Radboud data use agreement (Kern 2022 collection) if you use the wavs.

## Validation
**mlr tier, all 20 subjects** (600 trials), average reference over the 64 scalp channels without bads, played wav:
- **low:** mean r 0.046 (per subject 0.019-0.084), 20/20 subjects significant, TRF peak at 234 ms, nothing at
  negative lags. The shipped envelope gives the same result.
- **mlr (30-60 Hz):** SNR 1.81, p 0.010, 13/20 subjects significant. Peaks at ~22, 35 and 47 ms, flat at negative
  lags.
- **brainstem (30-250 Hz):** nominal pass only, SNR 1.10, p 0.030, 4/20 subjects. There is no wave V; the response
  is the MLR peak. The tier field of `validation.json` says `brainstem`, but the recorded tier is `mlr`.

**Suitable for** low-frequency and middle-latency responses to music, and for comparing musicians with
non-musicians.
**Not suitable for** brainstem analyses (512 Hz sampling, sparse piano onsets) or for effects of presentation order
(the order is unknown).

## Caveats
- `origTrialPosition` is empty, although the readme says it is included.
- The EEG units are not stated upstream (inferred as ADC counts).
- The authors' envelope method is not documented.
- The Dryad and Kern MIDI files differ (different exports). Neither is used.

Details: `notes.md`.
