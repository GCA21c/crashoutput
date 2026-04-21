# Preprocessing module

## Current implementation file
- `app/services/preprocessing/service.py`

## Role
- filtering, trimming, offset, derived-channel routing, and shared calculation-adjacent helpers
- UI pages and injury modules depend on this layer, so small helper moves can still create broad side effects

## Current split result
Phase 5 already separated several helper groups out of `service.py`.

Primary neighboring modules:
- `app/services/preprocessing/channel_roles.py`
- `app/services/preprocessing/timing.py`
- `app/services/preprocessing/offset.py`
- `app/services/preprocessing/series_ops.py`
- `app/services/preprocessing/channel_search.py`
- `app/services/preprocessing/filter_sources.py`
- `app/services/preprocessing/cfc_filter.py`

## High-risk areas
- filtering math and End Points behavior
- derived-channel orchestration
- HIC / 3ms shared helpers still connected to injury/report outputs
- neck, chest, femur calculation-adjacent helpers

## Maintenance rule
- preserve current public names exposed through `service.py` unless an explicit compatibility phase is approved
- treat preprocessing changes as cross-module changes and check DATA FILTERING, OFFSET/TRIMMING, INJURY, and REPORT entry paths together
- use direct user runtime testing instead of saved-`pkl` snapshot tooling
