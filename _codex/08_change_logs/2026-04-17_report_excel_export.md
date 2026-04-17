# Report Excel export

- Scope: `REPORT - SUMMARY` Excel export using `resources/templates/FMVSS208 Sumy_temp.xlsx`.
- Added `app/report/excel_export.py` to load the template with `openpyxl`, detect metadata anchors, detect IARV/RESULT columns, and write values only.
- Added `app/report/excel_summary_mapping.py` for template path, metadata anchors, and criteria label aliases.
- Changed `app/ui/pages/report_summary_page.py` to replace the placeholder Export action with `EXCEL EXPORT` and a save-as workflow.
- Added Excel export mapping documentation under `_codex/05_reference/excel_export_mapping.md`.
- Preserved calculation engines and SUMMARY REPORT snapshot calculation; export reads existing `value` and `limit` only.
- Risk: the current template supports two occupant groups; extra dummy slots are skipped and reported.
