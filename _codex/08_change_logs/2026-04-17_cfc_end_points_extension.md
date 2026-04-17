# CFC End Points Extension

## What changed
- Unified CFC filtering edge extension to `End Points`.
- Removed the previous zero-magnitude mirrored padding behavior from the shared CFC segment filtering path.
- Added derived-channel filter history metadata that records `extension_mode`.

## Why
- The program-wide filtering rule now requires all CFC filtering paths to extend the start with the first sample value and the end with the last sample value.

## Code scope
- `app/services/preprocessing/service.py`
  - `_apply_cfc_filter_segment()` now uses `_end_points_extend()`.
  - Manual filtering, derived CFC generation, injury target-CFC rebuilds, and neck CFC preparation all continue through the same CFC segment entry point.

## Risk
- This changes edge behavior for all CFC filtered outputs.
- SAE J211 coefficient calculation, `filtfilt` execution, CFC classes, and injury formulas were not changed.
