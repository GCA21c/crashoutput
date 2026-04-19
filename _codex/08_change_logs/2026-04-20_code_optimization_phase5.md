# 2026-04-20 code optimization phase 5

## What changed
- Created Phase 5 regression snapshot tooling before high-risk structure changes.
- Added a workflow document for snapshot capture and comparison.
- Added a placeholder folder for regression snapshot artifacts.
- Added an ignored input folder for representative saved `.pkl` files.
- Added snapshot-tool-only pandas StringArray pickle compatibility for previously saved files.
- Added folder-level snapshot capture/compare commands for Phase 5-B.
- Documented preprocessing service function groups and extraction risk.

## Why
- Phase 5 will touch higher-risk boundaries around preprocessing, injury preparation, and
  report/export contracts.
- A stable baseline is required before moving calculation-adjacent code.

## Files
- `.gitignore`
- `tools/capture_regression_snapshot.py`
- `_codex/03_workflows/regression_snapshot_workflow.md`
- `_codex/04_modules/preprocessing.md`
- `_codex/09_regression_snapshots/README.md`

## Risk
- No calculation logic changed.
- No runtime application path changed.
- Snapshot files may contain metadata and numeric digests from saved test data; review before sharing.
- Actual `.pkl` input files and generated snapshot JSON files are ignored by git by default.
