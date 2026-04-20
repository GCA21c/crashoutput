# Code optimization Phase 5-I-7

## What changed
- Documented the Phase 5-I closure boundary.
- Marked the remaining calculation-side functions in `app/services/preprocessing/service.py` as
  high-risk and outside the small-helper extraction sequence.

## Why
- Avoid mixing low-risk helper cleanup with formula-adjacent moves.
- Force the next step to start from a fresh high-risk boundary with regression checks.

## Risk
- No runtime code changed.
- The remaining work now clearly requires a separate approved slice.
