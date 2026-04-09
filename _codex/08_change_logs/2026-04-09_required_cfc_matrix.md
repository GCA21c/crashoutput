# Required CFC Matrix Documentation

## What changed
- Added `_codex/05_reference/required_cfc_matrix.md`.
- Summarized `test mode / regulation -> required CFC` rules for `head`, `neck`, `chest`, and `femur`.
- Linked the new reference from `_codex/04_modules/injury_engines.md` and `_codex/04_modules/filtering.md`.

## Why
- Upcoming calculation-time warnings should validate channels against rule-specific target CFC, not only against a generic module preference.
- Head, neck, chest, and femur already show regulation-specific differences in `Crash Analysis Criteria 2.4.3`.

## Impacted files
- `_codex/05_reference/required_cfc_matrix.md`
- `_codex/04_modules/injury_engines.md`
- `_codex/04_modules/filtering.md`

## Behavior impact
- No runtime code behavior change.
- Codex and future maintainers now have one source document for criterion-specific CFC validation rules.

## Regression risks
- Low. Documentation only.
- The matrix is intentionally limited to reviewed source sections and should not be over-generalized to uncovered modules yet.

## Next checks
- Extend the matrix to pelvis, knee, tibia, and iliac after source review.
- Use this matrix when implementing calculation-time warning and user-confirmed rebuild flow.
