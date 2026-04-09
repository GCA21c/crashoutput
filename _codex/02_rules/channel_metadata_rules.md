# Channel Metadata Rules

## Purpose
- `channel_metadata_map` is the single source of truth for per-channel filter state, ISOCODE state, and source lineage.
- Keep `result_uid` and `graph_uid` separate from channel metadata.
- Use channel metadata to decide calculation readiness, not channel name text alone.

## Current architecture
- `result_uid`
  - identifies one saved injury-result instance for a slot and section.
- `graph_uid`
  - identifies one saved graph instance for a slot and graph mode.
- `channel_metadata_map`
  - identifies channel provenance and filter readiness.

These must stay separate:
- UID layer = result/graph persistence identity
- channel metadata layer = input-channel provenance and validation

## Required channel metadata fields
- `channel_name`
- `source_channel`
- `root_source_channel`
- `lineage_type`
- `purpose`
- `role`
- `current_filter_label`
- `current_filter_code`
- `source_filter_label`
- `required_cfc`
- `display_filter_label`
- `created_from_raw`
- `rebuild_policy`
- `double_filter_safe`
- `filter_history`
- `raw_isocode`
- `managed_isocode`
- `isocode_parsed`
- `dummy_position`
- `sensor_family`
- `validation`

## Interpretation rules
- `source_channel`
  - immediate parent channel for a derived channel.
- `root_source_channel`
  - traced physical/raw source channel. This is the main provenance anchor.
- `current_filter_label`
  - effective current filter state used by calculations and display.
- `current_filter_code`
  - ISOCODE-compatible filter code derived from the effective filter state.
- `created_from_raw`
  - must be `True` when a derived channel was rebuilt directly from a raw-aligned source.
- `rebuild_policy`
  - if set to `raw_aligned_only`, any fallback path must be treated as lower confidence.
- `filter_history`
  - append-only lineage summary for how a filter state was created.
- `validation`
  - computed readiness flags. These are for calculation gating and future warnings.

## Non-negotiable rules
- Never decide that a channel is calculation-ready from its name suffix alone.
- Prefer `channel_metadata_map[channel]["current_filter_label"]` over `channel_filter_labels[channel]`.
- Prefer `channel_metadata_map[channel]["managed_isocode"]` over parsing the channel name text again.
- Use `root_source_channel` when deciding whether a derived channel is safe for re-filtering or comparison.
- Do not treat `managed_isocode` as a substitute for lineage. ISOCODE expresses state; lineage explains origin.
- `result_uid` and `graph_uid` must not be repurposed as channel identity keys.

## Filtering rules
- Filtering save/commit must keep these in sync:
  - dataframe columns
  - `channel_filter_labels`
  - `derived_channels`
  - `isocode_raw_map`
  - `isocode_managed_map`
  - `isocode_parsed_map`
  - `channel_metadata_map`
- If a channel filter label changes, rebuild `channel_metadata_map`.
- If a derived channel is renamed because of ISOCODE filter-code rewrite, metadata keys must be renamed together.

## Injury-calculation rules
- Head, neck, chest, femur, and future injury modules should read calculation readiness from channel metadata first.
- If a calculation uses a resolved helper/derived channel, pass the effective filter label of the resolved channel, not only the originally selected UI channel.
- For chest VC:
  - `ECE` path and `SAE J1727` path are separate.
  - the `SAE` displacement path should be treated as trustworthy only when the relevant channel metadata confirms raw-based creation or an equivalent validated path.
- For any required-CFC calculation:
  - first check channel metadata for filter match,
  - only rebuild from raw when no compliant validated path exists.

## Preferred future workflow
1. Resolve channel candidates by ISOCODE + metadata.
2. Confirm effective filter readiness from `channel_metadata_map`.
3. Confirm raw provenance when the rule requires raw-based rebuilding.
4. Only then enter the injury calculation.
5. Save result payloads with `result_uid` and `graph_uid` unchanged.

## When adding new channels
- If a new derived/calculated channel is created, update:
  - `descriptions`
  - `units`
  - `channel_filter_labels`
  - `derived_channels`
  - `channel_metadata_map` via the normal metadata rebuild path
- New derived metadata should include, when applicable:
  - `source_channel`
  - `purpose`
  - `role`
  - `filter_label`
  - `display_filter_label`
  - `required_cfc`
  - `created_from_raw`
  - `rebuild_policy`

## What to avoid in future work
- Do not add a second ad hoc metadata map for filter/lineage state.
- Do not let UI-only labels become the only source of filter truth.
- Do not bypass metadata rebuild after filtering, dataset stage save, or derived-channel creation.
- Do not infer raw-based safety from `CFC` label equality alone.

## Practical review checklist
- Did the changed module read `channel_metadata_map` where filter readiness matters?
- Did the change preserve `result_uid` and `graph_uid` as result/graph identity only?
- Did any new derived channel preserve `root_source_channel` traceability?
- Can the code distinguish:
  - selected channel,
  - resolved calculation channel,
  - root raw source channel?
- If `SAE/ECE` or multiple target CFC paths coexist, is each path represented explicitly in metadata?
