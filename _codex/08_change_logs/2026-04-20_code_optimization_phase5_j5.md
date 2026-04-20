# Code optimization Phase 5-J-5

## What changed
- Documented the remaining high-risk injury calculation bodies that still live in
  `app/services/preprocessing/service.py`.
- Captured caller modules, result-payload coupling, and the preferred extraction order:
  femur first, neck second, chest last.

## Why
- The helper-level extractions are effectively finished.
- The next moves are calculation-body moves and need an explicit boundary so they are not mixed
  together or treated as low-risk cleanup.

## Where
- `_codex/04_modules/preprocessing.md`
- `_codex/03_workflows/refactor_phase_tracker.md`

## Risk
- No runtime change in this slice.
- The next runtime slice remains high-risk because these functions feed saved payloads, report keys,
  and Excel export rows.
