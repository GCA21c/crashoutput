# Code optimization Phase 5-J-3

## What changed
- Added `app/services/injury/legacy_metrics.py`.
- Moved the legacy `compute_injury_metrics()` wrapper out of
  `app/services/preprocessing/service.py`.
- `service.py` now imports the helper and preserves the same public name.

## Why
- Clear one more legacy calculation-adjacent wrapper out of `service.py` without touching the
  underlying formulas.

## Risk
- Low.
- This wrapper reuses already-extracted HIC / 3ms / Nij helpers and keeps the same labels and
  return shape.
