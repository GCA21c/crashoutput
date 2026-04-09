# Channel Metadata Integration

## What changed
- Added a unified `channel_metadata_map` builder in `app/core/isocode/engine.py`.
- Combined filter label, filter code, raw/managed ISOCODE, parsed ISOCODE, source lineage, raw-based creation flags, and validation flags into one per-channel metadata object.
- Wired `app/shell.py` to rebuild `channel_metadata_map` whenever dataset metadata is enriched.
- Updated `app/ui/viewer_module.py` to prefer unified channel metadata when reading stored filter state and derived-channel info.
- Updated `app/ui/pages/injury_page.py` to read channel metadata for parsed ISOCODE and filter-code lookups.
- Updated chest injury calls so `accel_filter_labels` reflect the actually used calculation channels rather than only the originally selected channel names.

## Why
- The repository had filter labels, derived lineage, and ISOCODE parsing spread across separate metadata maps.
- Chest acceleration calculation could re-run `raw -> CFC180` even when the effective calculation channel had already been resolved to a `CFC180` path upstream.
- A unified channel metadata object provides a single source of truth for calculation readiness, traceability, and future validation rules.

## Impacted files
- `app/core/isocode/engine.py`
- `app/core/isocode/__init__.py`
- `app/shell.py`
- `app/ui/viewer_module.py`
- `app/ui/pages/injury_page.py`

## Behavior impact
- Dataset metadata now includes `channel_metadata_map`.
- UI and calculation helpers can read filter/isocode/lineage state from one map instead of reconstructing it ad hoc.
- Chest injury calculation now passes the effective filter label of the resolved accel channel, which reduces duplicate raw-based CFC180 regeneration when the upstream resolver already selected a compliant channel.

## Regression risks
- Medium metadata integration risk because multiple modules now depend on the new `channel_metadata_map`.
- Existing code paths that still read only `channel_filter_labels` or `derived_channels` remain supported, but mixed old/new assumptions should be reviewed.
- Sampling-rate validation is still not enforced; the new metadata structure only prepares the ground for that check.

## Next checks
- Verify filtering save/load keeps `channel_metadata_map` synchronized after repeated `_F` stage saves.
- Verify HEAD, CHEST, and NECK auto-channel selection still prefer the intended channels after metadata enrichment.
- Compare CHEST one-peak and multi-peak 3ms values before/after this change on a known dataset to confirm the expected reduction in duplicate CFC180 regeneration effects.
