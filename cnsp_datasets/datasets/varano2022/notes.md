# varano2022 notes

AVbook audiovisual speech in noise: 19 subjects x 55 trials (11 conditions x 5), 63-channel EEG at 1 kHz, split into
one fif per trial with 1.995 s of EEG before and after the stimulus (`data_2020/split_trials/unprocessed/raw`).

## Conditions
File token `<video>_<modality>`: video 1e envelope dot, 1m mismatched dot (1e video of another story part),
4v cartoon (face-landmark lines), bw edge detection, nh natural; modality AV or V0 (video only); `00` is audio only
(`A0` in the condorder files). Speech was presented in noise (the noise is not shipped; the logs give signal and
noise RMS, about -2 dB SNR). The previous adaptor had cartoon and edge swapped (4v is the cartoon, bw the edge
detection, per the readme and `EEG_stimuli/code`).

## Trial -> stimulus mapping
- `condorders/cond_orders/condorder_sub<N>.csv` lists trials in presentation order (two `setup` rows have no EEG).
  The file number `<k>` (0-4) counts trials within a condition; the condorder README calls it `trial_index`, which
  is wrong.
- Checked: ordering files by (`meas_date`, `first_samp`) reproduces `trial_index` order for every subject (3
  recordings each; subject 7's recording with trials 20-36 is dated 2020-10-14, after the other two).
- Checked: every trial lasts its wav + 2 x 1.995 s to the ms; mismatched AV trials last the shorter of the audio and
  video parts (in all 95), while the logs show the full audio was loaded, so the EEG stops at the video's end.
- Experiment logs (`data_2020/experiment_logs`) agree with the condorders (wav, video and cut length) where a log
  has one run; subjects 7 and 14 have restarted runs in their logs, sub 15 has no log, and the sub 24/25 logs are
  from the GRID behavioural experiment.

## Alignment
- No stimtrack in the shipped files (the authors' code mentions Sound and diode channels in the original
  recordings). The speech onset is nominal: 1.995 s into each file. The authors' aligned 200 Hz stimuli
  (`split_trials/stim/stim_dwnspl`) also start exactly 1.995 s in (113 of 113 trials checked).
- Units: volts, ~12 uV RMS after 1-40 Hz; large DC offsets in the unfiltered data.

## Standardised format
- Speech: `AVbook/A/<part>.wav` (clean, 48 kHz) cut to the trial, and `F/<part>.TextGrid` (word and phone tiers,
  lengths match the wavs; not cut for shortened mismatched trials).
- V0 and mismatched AV trials also get a `visual` stimulus: the speech of the story part shown in the video (not
  played). The videos themselves are not included yet (`EEG_stimuli/<video>/fNN.mp4`, `AVbook/V`).
- Extracting AVbook from the archive dumps files into the download root (not ideal).

## Open
- Behavioural data (`behavioural`, `QandA.csv`) is not included yet.
