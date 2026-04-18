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
- Closed Phase 1 after user acceptance and normal whole-program testing.
- Updated the file responsibility map for the new runtime export helper.
- Started Phase 2-A by adding shared UI style constants and applying them only to
  `app/shell.py` and `app/ui/pages/report_ploting_page.py`.
- Closed Phase 2-A after user confirmed normal program behavior.
- Started Phase 2-B by moving REPORT SUMMARY presentation constants out of
  `app/ui/pages/report_summary_page.py` into `app/ui/pages/report_summary_constants.py`.
- Closed Phase 2-B after user confirmed normal behavior.
- Started Phase 2-C by moving remaining REPORT SUMMARY messagebox/history/status text
  templates into `app/ui/pages/report_summary_constants.py`.
- Closed Phase 2-C after user confirmed normal behavior.
- Started Phase 2-D by adding small REPORT dialog helper wrappers in
  `app/ui/pages/report_summary_page.py`.
- Closed Phase 2-D after user confirmed normal behavior.
- Started Phase 2-E by centralizing REPORT SUMMARY loaded-count display formatting.
- Closed Phase 2-E after user confirmed normal behavior.
- Started Phase 2-F by reusing the REPORT SUMMARY input-variable helper for trace,
  restore, serialization, and reset paths.
- Closed Phase 2-F after user confirmed normal behavior.
- Started Phase 2-G by moving REPORT SUMMARY Valuation status selection into a small helper.

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
- Phase 2-A is a UI constant split only. It should not affect calculation, report payload,
  filtering, or export contracts.
- Phase 2-B is also presentation-only. Summary payload keys, Excel export behavior,
  save/load metadata, filtering, and injury calculations are unchanged.
- Phase 2-C keeps the same save/export call flow and only changes where report summary
  messages are defined.
- Phase 2-D keeps the same save/export call flow and only centralizes REPORT messagebox
  title usage.
- Phase 2-E keeps the same restore/valuation flow and only centralizes loaded-count
  display formatting.
- Phase 2-F keeps report field keys and metadata structure unchanged while reducing
  repeated input-variable handling.
- Phase 2-G keeps Valuation behavior unchanged and only moves existing status selection
  into a helper.
