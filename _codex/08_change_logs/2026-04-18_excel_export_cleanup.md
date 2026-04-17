# Excel export cleanup

## What
- Removed the tiny `app/report/excel_mapping.py` module and moved `build_excel_mapping()` into `app/report/mapping.py`.
- Kept the saved `excel_mapping` payload key for backward compatibility.
- Removed the duplicate numeric export wrapper by making `round_for_excel_export()` the single Excel numeric formatter.
- Collapsed occupant slot fallback helpers inside `app/report/exporters/excel.py`.

## Why
- Reduce report/export mapping file count and avoid duplicated naming around Excel mapping.
- Keep Excel export behavior stable while removing cleanup debt from earlier troubleshooting.

## Where
- `app/report/exporters/excel.py`
- `app/report/engine.py`
- `app/report/__init__.py`
- `app/report/excel_mapping.py` removed

## Risk
- Scope is limited to report/export helper organization.
- Summary row generation, calculation logic, Excel template mapping rules, and export output behavior are unchanged.
