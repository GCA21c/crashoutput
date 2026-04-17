# Report Excel openpyxl save restoration

## What
- Removed direct XLSX worksheet XML patching from `app/report/excel_export.py`.
- Excel export now writes values to existing template cells through `openpyxl` and saves the workbook normally.

## Why
- Directly patching `xl/worksheets/sheet1.xml` can leave stale workbook internals such as `xl/calcChain.xml`.
- Excel reported repair warnings for generated workbooks, including sheet XML and calculation-chain records.

## Where
- `app/report/excel_export.py`
- `_codex/04_modules/report.md`

## Risk
- Scope is limited to Excel file writing mechanics.
- Calculation logic, report value selection, C9/G9 occupant selection, and template mapping rules are unchanged.
- `openpyxl` may remove stale calculation-chain metadata during save; this is expected and lets Excel recalculate.
