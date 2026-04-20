# 2026-04-20 deferred DAT 215 loader fix

## What changed
- No runtime code changed.
- Documented a confirmed DAT loader policy issue and explicitly deferred the fix until the current
  code-optimization track is complete.

## Confirmed issue
- `app/services/io/dat_loader.py` currently reads DAT header field `215` as a no-value sentinel.
- When the header contains `215=-1`, the loader rewrites raw integer sample `-1` to `0` before
  applying channel `240`/`241` offset/scale conversion.
- On the uploaded `raw_dat_check.zip`, this behavior changes actual raw values for many channels.
- This means the current loader can alter measured raw samples by policy before any offset,
  filtering, trimming, or injury logic runs.

## Evidence
- `raw_dat_check.zip` reproduces the issue on `B1CHST0000H3ACYP`.
  - header `240=0.313513533979479`
  - header `241=0.104504511326493`
  - header `215=-1`
  - raw integer sample `-1` should convert to `0.209009...`
  - current loader converts the same sample to `0.313513...`
- `111.xlsx` second sheet matches the reference interpretation and shows the same `0.209009...`
  raw values at the mismatching chest-Y rows.
- The same `215=-1` rewrite path affects many channels in the same dataset, so this is not a
  chest-only exception.

## Why deferred
- The ongoing code-optimization work is currently focused on structure-preserving refactors.
- Changing DAT loader policy would alter raw input values and can cascade into offset, filtering,
  injury, report, and snapshot outputs.
- This must be handled as a separate behavior-change task with dedicated regression comparison.

## Required direction for the future fix
- Unknown or unverified DAT `215` values must not be arbitrarily rewritten to `0`.
- If the format meaning of `215` is not proven for the active dataset, preserve the imported raw
  sample as-is until an explicit rule is chosen.
- If a missing-data policy is still needed for some DAT variants, use a documented and testable
  rule rather than a silent blanket `-1 -> 0` conversion.

## Reopen checklist
- Use `raw_dat_check.zip` as the primary reproduction input.
- Use `111.xlsx` second sheet as the reference raw export.
- Compare before/after raw, offset, and filtered values for:
  - HEAD
  - CHEST
  - PELVIS
- Decide one loader policy explicitly:
  - ignore DAT `215`
  - honor DAT `215` conditionally
  - map `215` hits to `NaN` instead of `0`
- Do not keep the current blanket rewrite-to-zero behavior unless independent source material proves
  that the dataset really uses `215` as a raw no-value sentinel.
- Re-run representative regression snapshots after the loader policy decision.

## Risk
- This future fix is calculation-adjacent because it changes the earliest imported signal values.
- It must not be mixed into the remaining optimization phases without explicit user approval.
