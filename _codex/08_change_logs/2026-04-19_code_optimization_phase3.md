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
- Closed Phase 3-C after user testing passed.
- Implemented Phase 3-D Excel occupant label helper reuse:
  - moved shared occupant label formatting and slot-label dummy-name extraction into `app/report/occupants.py`
  - kept Excel exporter wrapper function names
  - left `_occupant_slot_infos()` merge/fallback flow and C9/G9 cell selection unchanged
- Closed Phase 3-D after user testing passed.
- Implemented Phase 3-E Excel occupant slot merge helper reuse:
  - `_occupant_slot_infos()` remains in the Excel exporter
  - final merge delegates to `merge_occupant_slots()`
  - source precedence and C9/G9 cell selection remain unchanged
- Closed Phase 3-E after user testing passed.
- Implemented Phase 3-F Excel occupant slot info wrapper:
  - added `occupant_slot_infos_from_snapshot()` to `app/report/occupants.py`
  - kept Excel `_occupant_slot_infos()` as a wrapper
  - source precedence and C9/G9 cell selection remain unchanged
- Closed Phase 3-F after user testing passed.
- Implemented Phase 3-G REPORT field assembly helper:
  - added `report_fields_from_sources()` to `app/report/occupants.py`
  - kept `ReportSummaryPage._report_fields()` as the page entry point
  - preserved current config / metadata config / saved fields / snapshot / saved summary precedence
- Implemented Phase 3-H Excel unused wrapper cleanup:
  - removed unused Excel private wrappers for slot normalization and slot-label dummy-name extraction
  - kept active Excel occupant wrappers and C9/G9 cell selection unchanged
- Closed Phase 3-G/H after user testing passed.
- Implemented Phase 3-I REPORT SUMMARY occupant wrapper closure:
  - removed unused `ReportSummaryPage._occupant_slots_from_config()`
  - removed unused `ReportSummaryPage._merge_occupant_slots()`
  - kept `ReportSummaryPage._report_fields()` as the page entry point
- Closed Phase 3-I after user testing passed.
- Closed Phase 3 at the occupant helper boundary:
  - kept report engine slot identity unchanged
  - deferred calculation-adjacent helper commonization until stronger numeric regression coverage exists
  - left Phase 4 as the next explicitly approved orchestration-split phase

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
- Phase 3-D changes only wrapper helper delegation for Excel occupant labels.
- Phase 3-E changes only the internal merge helper used by Excel occupant slot resolution.
- Phase 3-F changes only helper location behind the existing Excel wrapper.
- Phase 3-G changes only helper location behind the existing REPORT SUMMARY `_report_fields()` entry point.
- Phase 3-H removes unused Excel private wrapper code only.
- Phase 3-I removes unused REPORT SUMMARY wrapper methods after user testing confirmed the helper path.
- Phase 3-J is documentation-only closure and does not change runtime code.
- Filtering, injury calculation, report extraction, payload keys, metadata keys, and
  Excel writer behavior remain untouched.
