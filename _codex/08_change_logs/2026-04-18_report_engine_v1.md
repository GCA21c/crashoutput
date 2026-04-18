# Report engine v1

## What
- Introduced a modular REPORT structure:
  - `app/report/engine.py` for report snapshot/value extraction
  - `app/report/rules/fmvss208.py` for the current FMVSS 208 rule items
  - `app/report/templates/fmvss208_summary.py` for the current Excel template binding
  - `app/report/exporters/excel.py` for Excel export
  - `app/report/registry.py` for rule/template lookup
- Removed old `mapping.py`, `excel_export.py`, `excel_summary_mapping.py`, and `regulations/` files after moving their responsibilities.

## Why
- Future frontal, side, and other regulation reports should be added by registering new rule specs and template specs without rewriting the report engine.
- FMVSS 208 remains the only active rule/template in this first version.

## Where
- `app/report/engine.py`
- `app/report/registry.py`
- `app/report/rules/fmvss208.py`
- `app/report/templates/fmvss208_summary.py`
- `app/report/exporters/excel.py`
- `app/ui/pages/report_summary_page.py`

## Risk
- Scope is report organization and Excel export plumbing only.
- Injury calculations, filtering, limits, and report item values are unchanged.
