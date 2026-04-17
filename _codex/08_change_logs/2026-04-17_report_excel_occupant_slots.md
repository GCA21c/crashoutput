# Report Excel occupant slot fallback

## What
- Strengthened REPORT Excel export occupant-label sourcing for C9/G9.
- `ReportSummaryPage._report_fields()` now merges TEST SETUP slot metadata from current workbench config, dataset metadata, saved report fields, current snapshot, and saved summary slots.
- Excel occupant labels now prefer explicit report field slot metadata over snapshot fallback data.

## Why
- C9/G9 labels are slot-based TEST SETUP data, not injury result UID data.
- Saved or reloaded report sessions may have the needed B1/B2 dummy name/profile in metadata even when the current shared config is blank/default.

## Where
- `app/ui/pages/report_summary_page.py`
- `app/report/excel_export.py`

## Risk
- Scope is limited to export/report field metadata assembly.
- Injury calculations, filtering, summary value extraction, and template styles are unchanged.
