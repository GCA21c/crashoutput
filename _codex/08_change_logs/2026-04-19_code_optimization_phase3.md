# Code optimization Phase 3

## What changed
- Created Phase 3 planning state on branch `코드최적화p1_phase3`.
- Documented Phase 3-A snapshot comparison criteria before helper code movement.
- Marked Phase 3-A as reviewed and documented Phase 3-B occupant helper usage analysis.
- Added the Phase 3 helper refactor gate to:
  - `_codex/03_workflows/refactor_phase_tracker.md`
  - `_codex/03_workflows/refactor_master_plan.md`
  - `_codex/04_modules/report.md`
- Added the first implementation boundary for occupant helper extraction:
  - first move only pure `report_summary_page.py` slot helpers
  - keep page wrappers
  - leave Excel exporter and report engine behavior unchanged
- Implemented Phase 3-C first helper extraction:
  - added `app/report/occupants.py`
  - moved only pure occupant slot normalization/config extraction/merge helpers
  - kept `report_summary_page.py` wrapper methods
  - left `_report_fields()`, Excel exporter occupant fallback, and report engine slot identity unchanged

## Why
- Phase 3 helper commonization can indirectly change report values, occupant labels,
  saved report payloads, or Excel export output.
- Snapshot comparison criteria must be explicit before moving helper logic.
- Occupant label handling exists in report summary, Excel export, and report snapshot
  building with similar but not identical precedence rules.
- Moving all occupant paths at once would make C9/G9 export regressions harder to isolate.

## Risk
- Phase 3-A/B were documentation-only.
- Phase 3-C changed helper location but preserved wrapper methods.
- Filtering, injury calculation, report extraction, payload keys, metadata keys, and
  Excel writer behavior remain untouched.
