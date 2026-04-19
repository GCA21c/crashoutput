# Raw Reference Policy

## Purpose
This note defines what "raw" means in the current preprocessing and injury workflow.

## Workflow baseline
The intended order is:
1. `DATA OFFSET`
2. `DATA FILTERING`
3. `DATA TRIMMING`
4. injury calculations

Because of this order, the reference dataset for any later CFC rebuild is not the very first loaded DAT signal.

## Definition
`raw reference` means:
- offset already applied
- filtering not yet applied
- trimming not yet applied

In code this baseline is stored as:
- `workbench.pre_filter_reference_df`
- `workbench.pre_filter_reference_time_column`

## Why this matters
If a missing target CFC path is rebuilt from the first-loaded DAT raw:
- offset corrections are lost
- derived CFC channels can disagree with the current working dataset
- injury calculations can mix offset-applied selected channels with offset-before raw rebuilds

If a missing target CFC path is rebuilt from an already filtered channel:
- double filtering can occur
- channel lineage becomes unclear

## Current policy
- `DATA OFFSET` commit updates `pre_filter_reference_df`
- `DATA FILTERING` derived CFC generation rebuilds from `pre_filter_reference_df`
- injury calculations also rebuild missing target CFC paths from `pre_filter_reference_df`
- trimming must not redefine the raw reference baseline

## Affected calculation paths
- head target CFC resolution
- neck target CFC resolution
- chest acceleration/displacement target CFC resolution
- femur target CFC resolution
- preprocessing-derived CFC helper channels

## Persistence rule
- when saving a pickle, `pre_filter_reference_df` and its time-column metadata must be saved too
- when reopening a pickle, the same reference baseline must be restored
- `DATA OFFSET` may also save `offset_preview_before_df` for the UI-only "before offset"
  graph overlay. This is not a raw reference baseline and must not be used by filtering or
  injury calculations.

## Review points for future changes
- Does the code rebuild from `pre_filter_reference_df` when target CFC is missing?
- Does any path silently fall back to already filtered data?
- Does offset update the reference baseline exactly once?
- Does trimming leave the reference baseline untouched?
