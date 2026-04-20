# Code optimization Phase 5-I-5

## What changed
- Added `app/services/injury/chest_units.py`.
- Moved small chest-specific unit helpers out of `app/services/preprocessing/service.py`:
  - `convert_accel_to_g_series`
  - `convert_disp_to_mm_series`
  - `pick_compression_positive`
- Kept legacy private names `_convert_accel_to_g_series`, `_convert_disp_to_mm_series`, and
  `_pick_compression_positive` available from `service.py` through compatibility aliases.

## Why
- Continue the Phase 5 helper extraction sequence with small chest-preparation helpers.
- Reduce calculation-adjacent utility clutter in `service.py` while preserving behavior.

## Risk
- Medium.
- These helpers feed chest acceleration, displacement, and VC preparation, so the move must keep
  exact conversion and sign-preference semantics.
- No formula, threshold, IARV, report key, or pass/fail logic changed.
