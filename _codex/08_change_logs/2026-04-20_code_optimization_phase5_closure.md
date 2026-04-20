# Code optimization Phase 5 closure

## What changed
- Closed Phase 5 after user-tested runtime moves through Phase 5-J-8.
- Updated the phase tracker and preprocessing module notes to show the completed extraction boundary.

## Why
- The remaining high-risk calculation bodies were split into focused injury modules while preserving
  compatibility imports from `app/services/preprocessing/service.py`.

## Where
- `_codex/03_workflows/refactor_phase_tracker.md`
- `_codex/04_modules/preprocessing.md`

## Risk
- Documentation/status update only.
- Follow-up behavior changes remain deferred:
  - DAT loader `215` handling policy
  - viewer keyboard navigation numpy truth-value warning
