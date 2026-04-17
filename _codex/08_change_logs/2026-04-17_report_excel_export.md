# Report Excel export

- Scope: `REPORT - SUMMARY` Excel export using `resources/templates/FMVSS208 Sumy_temp.xlsx`.
- Added `app/report/excel_export.py` to load the template with `openpyxl`, detect metadata anchors, detect IARV/RESULT columns, and write values only.
- Added `app/report/excel_summary_mapping.py` for template path, metadata anchors, and criteria label aliases.
- Changed `app/ui/pages/report_summary_page.py` to replace the placeholder Export action with `EXCEL EXPORT` and a save-as workflow.
- Changed follow-up export behavior to save automatically in the execution folder using `{template_stem}_{test_id}.xlsx`, simplify the completion popup, and open the workbook after OK.
- Added two-decimal `ROUND_HALF_UP` export rounding for injury IARV/RESULT values.
- Added FMVSS 208 IARV exclusions for HIC36, head resultant 3ms, peak extension MOCy, and peak flexion MOCy.
- Added Excel export mapping documentation under `_codex/05_reference/excel_export_mapping.md`.
- Preserved calculation engines and SUMMARY REPORT snapshot calculation; export reads existing `value` and `limit` only.
- Risk: the current template supports two occupant groups; extra dummy slots are skipped and reported.
