# 2026-04-22 injury result store pilot

## What
- added `app/services/state/injury_result_store.py`
- treated `injury_saved_results` as canonical payload store
- synchronized `injury_result_registry`, `injury_graph_registry`, and new `injury_slot_registry`
- switched injury save / graph selection / reload hydration to the common store helper path
- switched report snapshot and plotting collection to read payloads through the common store helper
- added canonical metric payload blocks for `HEAD`, `NECK`, and `CHEST` under `canonical_metrics`

## Why
- result storage and lookup had drifted across `slot_states`, per-section saved payload caches, metadata payloads, and registry dicts
- NECK reload / plotting issues showed that consumers were not reading one source of truth

## Where
- `app/services/state/injury_result_store.py`
- `app/ui/pages/injury_page.py`
- `app/report/engine.py`
- `app/report/plotting_service.py`
- `app/services/state/injury_metric_canonical.py`

## Risk
- `slot_states` still remains as UI/runtime cache, so this is a pilot unification rather than full legacy removal
- graph rendering still rebuilds runtime metrics from slot state when arrays are not resident; payload store now hydrates that state first
- Windows runtime should be rechecked because `_I` reload, plotting load, and report snapshot all changed their lookup path
