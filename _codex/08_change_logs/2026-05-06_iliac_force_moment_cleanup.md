# ILIAC force/moment cleanup

## What changed
- Removed the ILIAC `Fx-My` graph tab and plotting graph mapping.
- Removed the ILIAC `sqrt(Fx^2 + My^2)` combined pulse from force graph display and metric payload.
- Changed ILIAC result summary to force/moment blocks:
  - force uses `Max(Tension)`, `Min(Compression)`, and `Abs Peak`.
  - moment uses `Max`, `Min`, and `Abs Peak`.
- Added ILIAC engineering rows to FMVSS 208 summary report without pass/fail limits.
- Kept plotting graph text split by graph type:
  - ILIAC Force uses Fx rows only.
  - ILIAC Moment uses My rows only.
- Removed THOR ASIS reference/source text from ILIAC summary output.
- Kept ILIAC scope only; no other injury calculation path was changed.

## Files
- `app/services/injury/iliac_injury.py`
- `app/ui/pages/injury_page.py`
- `app/services/state/injury_metric_canonical.py`
- `app/report/plotting_config.py`
- `app/report/plotting_service.py`
- `app/report/rules/fmvss208.py`
- `_codex/04_modules/report_plotting.md`

## Risk
- Existing saved payloads that still contain `crossplot` graph keys are normalized back to ILIAC force graph when rendered.
