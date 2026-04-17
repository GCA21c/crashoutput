# Report 3ms Rows and Excel Export Formatting

## What changed
- Added HEAD and CHEST `One Peak 3ms` / `Multiple Peak 3ms` rows to the FMVSS 208 SUMMARY REPORT item order.
- Kept the existing HEAD/CHEST acceleration 3ms criteria after the new one/multiple rows.
- Added Excel-only value transform rules for CHEST V*C RESULT export.
- Excel injury values are now written with exactly two decimal digits after `ROUND_HALF_UP` rounding.
- Added Excel-only RESULT source overrides so HEAD `Resultant Acc. 3ms Clip` and CHEST
  `Chest Acc. 3ms Clip` template rows export the `Multiple Peak 3ms` values.
- Excel export filenames now remove a trailing `_temp` from the template stem before
  appending the sanitized Test ID.

## Why
- SUMMARY REPORT needs to expose the existing one-peak and multiple-peak 3ms values for acceleration-based sections.
- CHEST V*C values must remain unchanged internally but export as positive values in Excel.

## Scope
- `app/report/regulations/fmvss208.py`
- `app/ui/pages/injury_page.py`
- `app/report/excel_export.py`
- `app/report/excel_summary_mapping.py`
- `_codex/04_modules/report.md`
- `_codex/05_reference/excel_export_mapping.md`

## Risk
- Current Excel template has no dedicated rows for the newly added HEAD/CHEST one/multiple 3ms criteria, so template export only writes rows present in the workbook.
- Calculation engines and injury formulas were not changed.
