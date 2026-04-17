# Report Excel occupant row fallback

## What
- Added Excel export fallback for C9/G9 occupant labels from SUMMARY REPORT rows.
- The exporter can now derive occupant labels from `slot_label` and `dummy_profile` when explicit TEST SETUP occupant metadata is missing.
- Occupant target cells are now detected from the `OCCUPANT` anchor using the same next-input-cell flow as the C2:C6 metadata fields; fixed `C9`/`G9` coordinates remain only as fallback.

## Why
- SUMMARY REPORT already displays the needed values in the Slot and Dummy columns.
- C9/G9 are fixed template occupant cells, so missing output was a source-data fallback issue rather than a merged-cell lookup issue.
- The anchor-based path keeps occupant writing aligned with the working metadata export path.

## Where
- `app/report/excel_export.py`

## Risk
- Scope is limited to Excel export occupant label source selection.
- Calculation logic, summary value extraction, and Excel template styles are unchanged.
