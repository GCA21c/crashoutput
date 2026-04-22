# 2026-04-22 injury result store pilot

## What
- added `app/services/state/injury_result_store.py`
- treated `injury_saved_results` as canonical payload store
- synchronized `injury_result_registry`, `injury_graph_registry`, and new `injury_slot_registry`
- switched injury save / graph selection / reload hydration to the common store helper path
- switched report snapshot and plotting collection to read payloads through the common store helper
- added canonical metric payload blocks for `HEAD`, `NECK`, and `CHEST` under `canonical_metrics`
- added canonical graph composition blocks for `HEAD`, `NECK`, and `CHEST` under `canonical_graphs`
- switched plotting text helpers to read canonical payload blocks first for `HEAD`, `NECK`, and `CHEST`, with legacy payload fields left as fallback
- added `calculation_context` payload blocks for `HEAD`, `NECK`, and `CHEST` so inputs, criterion/dummy, flags, and key parameters are stored separately from computed metrics
- switched `SUMMARY REPORT` extraction for `HEAD`, `NECK`, and `CHEST` to read canonical payload aliases first, with legacy aliases left as fallback
- added canonical metric payload blocks for `PELVIS`, `FEMUR`, `KNEE`, `ILIAC`, and `TIBIA`
- added canonical graph composition blocks for `PELVIS`, `FEMUR`, `KNEE`, `ILIAC`, and `TIBIA`
- added `calculation_context` payload blocks for `PELVIS`, `FEMUR`, `KNEE`, `ILIAC`, and `TIBIA`
- switched `SUMMARY REPORT` extraction for pelvis/femur/knee FMVSS rows to read canonical aliases first, with legacy aliases left as fallback
- added shared formatter payload access helpers so plotting/report can converge on one canonical/context read path instead of maintaining separate traversal logic

## Why
- result storage and lookup had drifted across `slot_states`, per-section saved payload caches, metadata payloads, and registry dicts
- NECK reload / plotting issues showed that consumers were not reading one source of truth

## Where
- `app/services/state/injury_result_store.py`
- `app/ui/pages/injury_page.py`
- `app/report/engine.py`
- `app/report/plotting_service.py`
- `app/report/formatters/payload_access.py`
- `app/services/state/injury_metric_canonical.py`
- `app/report/rules/fmvss208.py`

## Risk
- `slot_states` still remains as UI/runtime cache, so this is a pilot unification rather than full legacy removal
- graph rendering still rebuilds runtime metrics from slot state when arrays are not resident; payload store now hydrates that state first
- canonical graph composition is stored, but formatters still mostly read legacy graph-key-specific rules rather than the canonical graph layer
- Windows runtime should be rechecked because `_I` reload, plotting load, and report snapshot all changed their lookup path
