# AUTO SET Neck Force CFC1000

## What changed
- Updated the FRONTAL AUTO SET preset DB so `neck` + `force` maps to `CFC 1000`.
- Applied to both `H3_50%M` and `H3_5%F` profile records.

## Why
- NECK UPPER FORCE should be preset by the base mapping itself, not by an exception override.

## Scope
- `app/core/dummy/filter_presets.py`

## Risk
- AUTO SET pending preset behavior changes for neck force channels only.
- Injury calculation logic and filtering engine logic were not changed.
