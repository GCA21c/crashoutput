# Code optimization Phase 5-J-6

## What changed
- Moved `compute_femur_metrics()` from `app/services/preprocessing/service.py` to
  `app/services/injury/femur_metrics.py`.
- Kept the public import path stable by re-importing it from `service.py`.

## Why
- Phase 5-J-5 fixed the remaining calculation-body order.
- FEMUR has the smallest coupling among the remaining bodies, so it is the safest first move.

## Where
- `app/services/injury/femur_metrics.py`
- `app/services/preprocessing/service.py`
- `_codex/04_modules/preprocessing.md`
- `_codex/03_workflows/refactor_phase_tracker.md`

## Risk
- Runtime move only; no formula or payload-key change intended.
- Direct caller regression risk remains in FEMUR calculate, save/reopen, and report rows.
