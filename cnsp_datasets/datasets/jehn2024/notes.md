# jehn2024 notes

Not yet reviewed in the data campaign. One HDF5 archive (`ci_attention_final_l_1,1_h_32,50_out_125_130_incl_ica.hdf5`,
125 Hz; the file name suggests 1-32 Hz filtering and ICA) in the layout of the jehn2025 archives, read by the
jehn2025 adaptor (`Jehn2024Adaptor` subclasses `Jehn2025Adaptor`; see `jehn2025_base/notes.md`).

Differences from jehn2025, kept as before: the plain parity rule for the attended side (odd trials right; the
jehn2025 swaps ci 103, nh 305/306 were found on the 1 kHz aux channels and are not checked here), stimulus names
`<story>_<part>` without `_target`/`_distractor`, no drift correction.

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor is now a subclass of the jehn2025 adaptor (was a ~210-line copy); same output except: CI channels in
  `taken_out_indices` are kept and listed in `info["bads"]` (were dropped); stimulus audio is float32 (integer
  samples scaled to [-1, 1); float samples unchanged); a subject code whose first digit is not 1/2/3 raises.
