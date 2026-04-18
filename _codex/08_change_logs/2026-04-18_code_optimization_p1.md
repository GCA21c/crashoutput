# Code optimization P1

## What changed
- Added report naming and compatibility contract notes to `_codex/04_modules/report.md`.
- Added report snapshot regression criteria for future no-behavior-change refactors.
- Moved Excel export filename, output folder, duplicate-name, and OS open helpers from
  `app/ui/pages/report_summary_page.py` to `app/report/exporters/runtime.py`.
- Kept legacy `report_ploting` internals while correcting user-facing PLOTTING labels and
  adding `report_plotting` as a forward page-key alias.
- Documented that `dummyset` and `DummySetPage` compatibility shims must remain during
  Phase 1 naming cleanup.
- Added `_codex/03_workflows/refactor_master_plan.md` to pin the full refactoring direction.
- Added `_codex/03_workflows/refactor_phase_tracker.md` to track the current phase and
  prevent accidental phase skipping.
- Marked Phase 1-C as ready for user test after keeping all compatibility aliases and
  documenting stable report rule/template naming in code comments.
- Documented Phase 1-D rename candidate decisions in the master plan and phase tracker.
- Documented Phase 1-E decision to defer actual internal key/class/file renames from
  this branch.
- Updated the file responsibility map for the new runtime export helper.

## Why
- Keep REPORT page code focused on UI flow while moving export runtime concerns into
  the report/exporter boundary.
- Establish compatibility rules before larger cleanup around page keys, report keys,
  template keys, and saved metadata keys.
- Keep the refactoring sequence explicit so Phase 2 is not started before Phase 1 is
  closed and user-tested.

## Risk
- Calculation logic is not changed.
- Existing page keys remain available. The `report_ploting` typo is still the registered
  internal key, with `report_plotting` only accepted as an alias.
- Excel export path and open behavior should remain equivalent. Windows open behavior
  still depends on the OS file association and may need direct user verification.
