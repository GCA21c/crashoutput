# 2026-04-21 regression snapshot workflow improvement

- file: `tools/capture_regression_snapshot.py`
- change: added `verify-dir` to refresh an `after/` snapshot directory and compare it against an existing `before/` baseline in one command
- why: Phase 5 follow-up work repeats the same snapshot re-capture and compare loop, so the workflow needed a shorter verified path without touching calculation logic
- docs:
  - `_codex/03_workflows/regression_snapshot_workflow.md`
  - `_codex/03_workflows/refactor_phase_tracker.md`
  - `_codex/09_regression_snapshots/README.md`
- risk:
  - no runtime calculation path change
  - only regression-tool CLI and workflow documents changed
