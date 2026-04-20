# 2026-04-20 code optimization phase 5

## What changed
- Created Phase 5 regression snapshot tooling before high-risk structure changes.
- Added a workflow document for snapshot capture and comparison.
- Added a placeholder folder for regression snapshot artifacts.
- Added an ignored input folder for representative saved `.pkl` files.
- Added snapshot-tool-only pandas StringArray pickle compatibility for previously saved files.
- Added folder-level snapshot capture/compare commands for Phase 5-B.
- Documented preprocessing service function groups and extraction risk.
- Extracted preprocessing channel role detector helpers into a dedicated module for Phase 5-C.
- Extracted preprocessing numeric/time helpers into a dedicated module for Phase 5-D.
- Extracted preprocessing offset/trimming helpers into dedicated modules for Phase 5-E.
- Extracted viewer/channel search helpers into a dedicated module for Phase 5-F.
- Added DAT channel-order metadata and display-only channel prefixes for DATA FILTERING.
- Extracted filter source / raw-alignment helper functions into a dedicated module for Phase 5-G.
- Changed REPORT SUMMARY Excel export to let users choose the output path before saving.
- Documented CFC/filtering kernel call paths and high-risk boundary for Phase 5-H-1.
- Extracted the CFC filter kernel into a dedicated preprocessing module for Phase 5-H-2.
- Documented injury helper call paths and high-risk boundary for Phase 5-I-1.
- Extracted the resultant XYZ helper into a dedicated injury vector math module for Phase 5-I-2.

## Why
- Phase 5 will touch higher-risk boundaries around preprocessing, injury preparation, and
  report/export contracts.
- A stable baseline is required before moving calculation-adjacent code.

## Files
- `.gitignore`
- `tools/capture_regression_snapshot.py`
- `app/services/preprocessing/channel_roles.py`
- `app/services/preprocessing/timing.py`
- `app/services/preprocessing/offset.py`
- `app/services/preprocessing/series_ops.py`
- `app/services/preprocessing/channel_search.py`
- `app/services/preprocessing/filter_sources.py`
- `app/services/preprocessing/cfc_filter.py`
- `app/services/preprocessing/service.py`
- `app/services/injury/vector_math.py`
- `app/services/io/dat_loader.py`
- `app/ui/pages/filtering_page.py`
- `app/ui/pages/report_summary_page.py`
- `app/ui/viewer_module.py` (reviewed only)
- `app/ui/pages/injury_page.py` (reviewed only)
- `app/services/injury/*.py` (reviewed only)
- `app/services/injury/common_engines.py` (reviewed only)
- `_codex/03_workflows/regression_snapshot_workflow.md`
- `_codex/04_modules/preprocessing.md`
- `_codex/09_regression_snapshots/README.md`

## Risk
- No calculation logic changed.
- No runtime application path changed.
- Snapshot files may contain metadata and numeric digests from saved test data; review before sharing.
- Actual `.pkl` input files and generated snapshot JSON files are ignored by git by default.
- Phase 5-C keeps `service.py` as the compatibility import surface for moved detector helpers.
- Phase 5-D keeps `_get_sample_rate` available from `service.py` for compatibility.
- Phase 5-E keeps offset/trimming helper names available from `service.py` for compatibility.
- Phase 5-F keeps viewer/channel search helper names available from `service.py` for compatibility.
- DATA FILTERING prefixes such as `002:B1:` are display-only and are not used as data keys.
- Phase 5-G keeps filter source helper names available from `service.py` for compatibility.
- REPORT SUMMARY Excel export still opens the generated workbook after the completion dialog.
- Phase 5-H-2 keeps CFC kernel helper names available from `service.py` for compatibility.
