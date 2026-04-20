# Neck Peak Extension sign output

## What changed
- Removed the forced absolute-value display for `Peak Extension MOCy`.
- Removed the FMVSS208 report-rule transform that converted `peak_extension_my` to a positive value.

## Why
- `peak_extension_my` is already stored as the calculated signed extension peak.
- UI text output, SUMMARY REPORT, and Excel export should keep the same sign instead of silently
  converting it to positive.

## Where
- `app/services/injury/neck_injury.py`
- `app/report/rules/fmvss208.py`
- `_codex/08_change_logs/2026-04-14_report_summary_fmvss208_restructure.md`

## Risk
- Display/report behavior change only.
- Neck calculation math is unchanged.
