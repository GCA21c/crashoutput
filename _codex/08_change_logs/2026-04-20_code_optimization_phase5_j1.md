# Code optimization Phase 5-J-1

## What changed
- Documented the HIC / 3ms high-risk boundary in `_codex/04_modules/preprocessing.md`.
- Recorded active callers, shared helper coupling, and prohibited combined moves.

## Why
- The remaining calculation-side work is no longer small-helper cleanup.
- HIC / 3ms logic now needs a dedicated runtime slice with regression checks.

## Risk
- No runtime code changed.
- Future HIC / 3ms moves must preserve current bundle contracts, exact/exceedance helper meanings,
  and `use_high_res_cumulative_3ms` behavior.
