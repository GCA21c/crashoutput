# Code optimization P1

## What changed
- Added report naming and compatibility contract notes to `_codex/04_modules/report.md`.
- Added report snapshot regression criteria for future no-behavior-change refactors.
- Moved Excel export filename, output folder, duplicate-name, and OS open helpers from
  `app/ui/pages/report_summary_page.py` to `app/report/exporters/runtime.py`.
- Updated the file responsibility map for the new runtime export helper.

## Why
- Keep REPORT page code focused on UI flow while moving export runtime concerns into
  the report/exporter boundary.
- Establish compatibility rules before larger cleanup around page keys, report keys,
  template keys, and saved metadata keys.

## Risk
- Calculation logic is not changed.
- Excel export path and open behavior should remain equivalent. Windows open behavior
  still depends on the OS file association and may need direct user verification.
