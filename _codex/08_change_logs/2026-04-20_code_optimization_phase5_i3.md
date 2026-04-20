# Code optimization Phase 5-I-3

## What changed
- Added `app/services/injury/scalars.py`.
- Moved small pure scalar helpers out of `app/services/preprocessing/service.py`:
  - `series_to_float`
  - `convert_accel_to_g`
- Kept legacy private names `_series_to_float` and `_convert_accel_to_g` available from
  `service.py` through compatibility aliases.

## Why
- Continue the Phase 5 small-helper extraction sequence without touching formula bodies.
- Reduce calculation-adjacent utility clutter in `service.py` while preserving behavior.

## Risk
- Low to medium.
- These helpers feed HIC entry points and legacy `compute_injury_metrics()`, so the move must keep
  exact conversion semantics and import compatibility.
- No formula, threshold, IARV, report key, or pass/fail logic changed.
