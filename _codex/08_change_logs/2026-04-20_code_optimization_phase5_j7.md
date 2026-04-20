# Code optimization Phase 5-J-7

## What changed
- Moved `compute_neck_nij_metrics()` from `app/services/preprocessing/service.py` to
  `app/services/injury/neck_metrics.py`.
- Kept the public import path stable by re-importing it from `service.py`.

## Why
- NECK was the next calculation body after FEMUR in the documented Phase 5-J order.
- The move separates neck injury math from preprocessing orchestration without changing behavior.

## Where
- `app/services/injury/neck_metrics.py`
- `app/services/preprocessing/service.py`
- `_codex/04_modules/preprocessing.md`
- `_codex/03_workflows/refactor_phase_tracker.md`

## Risk
- Runtime move only; no formula or payload-key change intended.
- Direct caller regression risk remains in NECK calculate, calculated-channel persistence,
  save/reopen, and report rows.
