# Code optimization Phase 5-J-2

## What changed
- Added `app/services/injury/hic_3ms_math.py`.
- Moved HIC / 3ms math helpers out of `app/services/preprocessing/service.py`.
- Kept all legacy names available from `service.py` through import compatibility.

## Why
- Start the first approved high-risk calculation-side split at the HIC / 3ms boundary.
- Reduce calculation implementation density in `service.py` while preserving current contracts.

## Risk
- High.
- These helpers feed HEAD, CHEST, and PELVIS calculations directly and are also referenced through
  `common_engines.py` lazy imports.
- No formula, option, payload key, or public call shape was intentionally changed.
