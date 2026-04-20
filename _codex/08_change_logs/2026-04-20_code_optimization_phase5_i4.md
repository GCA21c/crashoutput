# Code optimization Phase 5-I-4

## What changed
- Added `app/services/injury/forces.py`.
- Moved small pure femur-force helpers out of `app/services/preprocessing/service.py`:
  - `normalize_force_to_n`
  - `peak_detail_abs`
- Kept legacy private names `_normalize_force_to_n` and `_peak_detail_abs` available from
  `service.py` through compatibility aliases.

## Why
- Continue the Phase 5 helper extraction sequence with low-risk force/unit helpers.
- Reduce calculation-adjacent utility clutter in `service.py` while preserving behavior.

## Risk
- Low to medium.
- These helpers feed femur value normalization and absolute-peak detail selection, so the move
  must keep exact conversion semantics and import compatibility.
- No formula, threshold, IARV, report key, or pass/fail logic changed.
