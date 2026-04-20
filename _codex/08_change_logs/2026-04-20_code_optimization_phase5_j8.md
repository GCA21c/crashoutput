# Code optimization Phase 5-J-8

## What changed
- Moved `compute_chest_metrics()` from `app/services/preprocessing/service.py` to
  `app/services/injury/chest_metrics.py`.
- Kept the public import path stable by re-importing it from `service.py`.

## Why
- CHEST was the last remaining high-risk calculation body in the Phase 5-J order.
- The move separates chest injury math and V*C preparation from preprocessing orchestration without
  changing behavior.

## Where
- `app/services/injury/chest_metrics.py`
- `app/services/preprocessing/service.py`
- `_codex/04_modules/preprocessing.md`
- `_codex/03_workflows/refactor_phase_tracker.md`

## Risk
- Runtime move only; no formula or payload-key change intended.
- Direct caller regression risk remains in CHEST calculate, V*C rows, save/reopen, SUMMARY REPORT,
  and Excel export.
