# Injury UI orchestration

## Main code paths
- `app/ui/pages/injury_page.py`
- `app/ui/pages/viewer_page.py`
- `app/ui/components/workbench_viewer.py`
- `app/ui/viewer_module.py`

## Responsibilities
- present injury modules and results
- coordinate selected dummy, test mode, and module state
- keep result summaries stable when navigating between modules/pages

## Review checklist
- Does module navigation preserve result state?
- Does dummy context propagate correctly from TEST SETUP to injury tabs?
- Do result summaries survive page switches?
- Are viewer labels aligned with the intended generated/result channels?

## HEAD graph notes
- `HEAD X/Y/Z` should display filtered HEAD X, Y, Z curves plus HEAD Resultant as an overlay.
- `HEAD RESULTANT` should display only HEAD Resultant, both HIC interval highlights, and the one Peak 3ms_Clip reference line.
- `HEAD RESULTANT` time axis should stay zoomed to `0 ~ 150 ms`.
- HEAD graph changes should stay in display logic only unless the task explicitly changes the injury calculation path.
- HEAD result summary should append the slot-scoped `FMVSS Head Acceleration 80g / 3ms Limit` check under `Resultant Acc. Peak`.
- The 80g / 3ms check uses the computed HEAD Resultant signal and stores total exceedance duration in milliseconds for report use.

## NECK graph notes
- `NECK FO` should overlay Fx, Fy, Fz.
- `NECK MO` should overlay Mx, My, Mz.
- `MOCy` and `UPPER NECK INDEX Nij` should remain separate tabs.
