# DAT 215 loader policy fix

## What changed
- Removed the DAT loader behavior that rewrote raw samples matching DAT header field `215` to `0`
  before applying `240`/`241` scale and offset conversion.
- Added `dat_channel_novalue_map` to DAT metadata so the header value is still inspectable without
  altering imported samples.

## Why
- The previous blanket rewrite could change real measured raw values before offset, filtering,
  trimming, or injury calculations.
- Verified reference comparisons showed channels such as `B1CHST0000H3ACYP` legitimately use raw
  integer `-1` as a real sample value, not as a value that should be forced to `0`.
- Unknown or unverified DAT `215` meanings must not silently mutate imported raw data.

## Where
- `app/services/io/dat_loader.py`

## Risk
- This is an early-input behavior change and can change raw/offset/filter/injury outputs for DAT
  files that previously hit the blanket rewrite path.
- The fix is intentionally limited to preserving raw samples and exposing the original `215` header
  only as metadata.
- Windows runtime should be checked because DAT import is cross-platform sensitive.
