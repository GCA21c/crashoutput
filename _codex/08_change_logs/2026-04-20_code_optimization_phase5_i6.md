# Code optimization Phase 5-I-6

## What changed
- Added `app/services/injury/nij_math.py`.
- Moved small pure Nij helpers out of `app/services/preprocessing/service.py`:
  - `compute_nij`
  - `compute_nij_series`
- `service.py` now imports those helpers and preserves the same public names.

## Why
- Continue the Phase 5 helper extraction sequence with isolated Nij math.
- Reduce calculation-adjacent utility clutter in `service.py` while preserving behavior.

## Risk
- Medium.
- These helpers feed neck/Nij results directly, so the move must keep exact coefficients and sign logic.
- No formula, threshold, IARV, report key, or pass/fail logic changed.
