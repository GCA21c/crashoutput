# Report 3ms Rows and Excel Export Formatting

## What changed
- Added HEAD and CHEST `One Peak 3ms` / `Multiple Peak 3ms` rows to the FMVSS 208 SUMMARY REPORT item order.
- Kept the existing HEAD/CHEST acceleration 3ms criteria after the new one/multiple rows.
- Removed the Excel-only positive transform for CHEST V*C RESULT export.
- SUMMARY REPORT and Excel export now read CHEST V*C values from each V*C MAX metric,
  not from the absolute max/min peak helper.
- Excel injury values are now written with exactly two decimal digits after `ROUND_HALF_UP` rounding.
- Added Excel-only RESULT source overrides so HEAD `Resultant Acc. 3ms Clip` and CHEST
  `Chest Acc. 3ms Clip` template rows export the `Multiple Peak 3ms` values.
- Excel export filenames now remove a trailing `_temp` from the template stem before
  appending the sanitized Test ID.
- Excel template resolution now checks packaged resource folders before the source-tree
  template path.
- Excel export output no longer uses `Path.cwd()`, avoiding Windows shortcut launches
  that point to `C:\Windows\System32`.
- Excel export writes TEST SETUP occupant labels to `C9` and `G9` without touching cell
  styles.
- Excel export no longer saves the workbook through `openpyxl`; it copies the template
  and patches worksheet XML values only to avoid merged-cell style rewrites.

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
