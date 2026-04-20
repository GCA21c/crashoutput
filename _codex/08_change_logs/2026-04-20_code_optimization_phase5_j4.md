# Code optimization Phase 5-J-4

## What changed
- Added `app/services/injury/neck_payloads.py`.
- Moved neck calculated-channel save helpers out of `app/services/preprocessing/service.py`:
  - `build_neck_injury_channels`
  - `build_neck_injury_channel_metadata`
- `service.py` now imports the helpers and preserves the same public names.

## Why
- Clear neck save/persistence helpers out of `service.py` without touching neck calculation logic.

## Risk
- Low to medium.
- These helpers affect `_I` saved calculated channels and their metadata, so the move must keep
  exact channel names and filter labels.
