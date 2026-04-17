# Report summary region, chest VC, and pelvis rows

- Scope: SUMMARY REPORT row definition, extraction, and table display.
- Changed `app/report/regulations/fmvss208.py` to add CHEST V*C SAE/ECE rows after `Chest Deflection Peak` and PELVIS 3ms/Res-Peak rows before FEMUR.
- Changed `app/report/mapping.py` to include an `Injury/Region` row field derived from the regulation item or `section_key`.
- Changed SUMMARY REPORT ordering to group rows by dummy slot first, then by the regulation item order.
- Changed `app/ui/pages/report_summary_page.py` to show and persist the region column in saved summary report rows.
- Changed saved summary report restore to re-sort old rows by slot and regulation item order when loading.
- Added `_codex/04_modules/report.md` with the report row-spec, payload-key, and output-order workflow.
- Preserved injury calculation engines, filtering, trimming, offset, and non-summary report behavior.
- Risk: verified with syntax/import checks and synthetic metadata; full Tk visual review was not run on Windows.
