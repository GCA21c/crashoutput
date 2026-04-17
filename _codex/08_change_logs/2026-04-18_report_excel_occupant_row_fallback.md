# Report Excel occupant row fallback

## What
- Added Excel export fallback for C9/G9 occupant labels from SUMMARY REPORT rows.
- The exporter can now derive occupant labels from `slot_label` and `dummy_profile` when explicit TEST SETUP occupant metadata is missing.

## Why
- SUMMARY REPORT already displays the needed values in the Slot and Dummy columns.
- C9/G9 are fixed template occupant cells, so missing output was a source-data fallback issue rather than a merged-cell lookup issue.

## Where
- `app/report/excel_export.py`

## Risk
- Scope is limited to Excel export occupant label source selection.
- Calculation logic, summary value extraction, and Excel template styles are unchanged.
