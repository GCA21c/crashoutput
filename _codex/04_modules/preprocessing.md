# Preprocessing module

## Current implementation file
- `app/services/preprocessing/service.py`

This file currently contains multiple responsibilities. Phase 5 must split it only after
regression snapshots are available and compared.

## Function groups
| Group | Current functions | Risk | Phase 5 action |
|---|---|---|---|
| Numeric/time helpers | `get_numeric_channels`, `get_time_numeric`, `find_time0_row`, `_get_sample_rate` | LOW to MEDIUM | Candidate for early extraction after snapshot compare loop is fixed |
| Trimming / offset | `trim_dataframe`, `get_offset_sample_rows`, `apply_offset` | MEDIUM | Keep behavior unchanged; extract only with `_O` / `_O_F` snapshot comparison |
| CFC filter kernel | `_cfc_coefficients_sae_j211`, `_end_points_extend`, `_apply_cfc_filter_segment`, `apply_cfc_filter_to_series` | HIGH | Do not change math or extension behavior; facade must preserve public API |
| Manual filtering | `apply_filtering`, `_replace_with_numeric_series`, `parse_cfc_filter_label` | HIGH | Move only after `_O_F` dataframe digest baseline is stable |
| Derived channel routing | `detect_*_channel_role`, `derived_role_required_cfc`, `detect_injury_channel_purpose_and_role`, `make_derived_channel_name`, `_resolve_*source*`, `apply_filtering_with_derivatives` | HIGH | Do not move `apply_filtering_with_derivatives()` first; split detectors before orchestration |
| Viewer auto-detect helpers | `make_channel_search_text`, `infer_channel_group_key`, `_find_resultant_or_axis`, `auto_detect_injury_channels` | MEDIUM | Later extraction candidate; can affect UI channel selection |
| HIC / 3ms common helpers | `_cumtrapz`, `_prepare_hic_series`, `_integral_at_query`, `_value_at_query`, `compute_hic_details`, `compute_3ms_*` | HIGH | Numeric injury outputs can change; require `_O_F_T_I` snapshot comparison |
| Neck helpers | `compute_nij*`, `build_neck_injury_channels`, `build_neck_injury_channel_metadata`, `compute_neck_nij_metrics` | HIGH | Keep until dedicated neck regression check exists |
| Chest helpers | `_convert_accel_to_g_series`, `_convert_disp_to_mm_series`, `compute_chest_metrics` and nested VC helpers | HIGH | Do not extract nested `_gradient_contiguous` without VC baseline comparison |
| Femur helpers | `_normalize_force_to_n`, `_peak_detail_abs`, `compute_femur_metrics` | MEDIUM to HIGH | Candidate after HIC/3ms/chest high-risk work is protected |

## Phase 5-B boundary
Phase 5-B is analysis and regression workflow only.

Allowed:
- document function groups
- add snapshot capture/compare workflow
- add non-runtime tooling

Not allowed:
- move functions out of `service.py`
- change CFC filtering math
- change End Points extension mode
- change HIC / 3ms / VC / Nij / femur formulas
- change public function names used by UI pages

## First extraction candidates after Phase 5-B
1. Constants and labels that have no numeric effect.
2. Pure detector helpers before `apply_filtering_with_derivatives()`.
3. Numeric/time helpers only if snapshot comparison confirms no dataframe/report changes.

`apply_filtering_with_derivatives()`, `_apply_cfc_filter_segment()`,
`compute_hic_details()`, `compute_3ms_*`, `compute_chest_metrics()`, and
`compute_neck_nij_metrics()` remain high-risk and must not be moved first.

## Phase 5-C channel role detector extraction
Implemented first extraction:

- new module: `app/services/preprocessing/channel_roles.py`
- moved pure string/role helpers:
  - `_safe_text`
  - `detect_head_channel_role`
  - `detect_chest_channel_role`
  - `detect_femur_channel_role`
  - `detect_neck_channel_role`
  - `neck_role_required_cfc`
  - `derived_role_required_cfc`
  - `detect_injury_channel_purpose_and_role`
  - `make_derived_channel_name`
  - `make_neck_derived_channel_name`

Compatibility:
- `app/services/preprocessing/service.py` imports these names from the new module, so existing
  imports from `service.py` remain valid.

Not changed:
- `apply_filtering_with_derivatives()`
- `apply_filtering()`
- CFC filter kernel
- End Points extension
- HIC / 3ms / VC / Nij / femur calculation functions

Required verification:
- `capture-dir` after the move
- `compare-dir` against the Phase 5 baseline
- user startup and representative DATA FILTERING / INJURY entry test

## Phase 5-D numeric/time helper extraction
Implemented second extraction:

- new module: `app/services/preprocessing/timing.py`
- moved helpers:
  - `get_numeric_channels`
  - `get_time_numeric`
  - `find_time0_row`
  - `get_sample_rate`

Compatibility:
- `app/services/preprocessing/service.py` imports these names from the new module.
- legacy private import `_get_sample_rate` remains available from `service.py` as an alias
  to `timing.get_sample_rate`.

Not changed:
- `trim_dataframe`
- `get_offset_sample_rows`
- `apply_offset`
- CFC filter kernel and End Points extension
- `apply_filtering()` and `apply_filtering_with_derivatives()`
- HIC / 3ms / VC / Nij / femur calculation functions

Required verification:
- import compatibility for UI pages and viewer
- `capture-dir` after the move
- `compare-dir` against the Phase 5 baseline
- user startup, DATA OFFSET, DATA FILTERING, and representative INJURY entry test

## Phase 5-E offset/trimming helper extraction
Implemented third extraction:

- new module: `app/services/preprocessing/offset.py`
- new support module: `app/services/preprocessing/series_ops.py`
- moved helpers:
  - `trim_dataframe`
  - `get_offset_sample_rows`
  - `apply_offset`
  - shared value writer `replace_with_numeric_series`

Compatibility:
- `app/services/preprocessing/service.py` imports `trim_dataframe`, `get_offset_sample_rows`,
  and `apply_offset` from the new module.
- legacy private helper `_replace_with_numeric_series` remains available from `service.py` as
  an alias to `series_ops.replace_with_numeric_series`.

Not changed:
- offset sample-row rule
- offset mean calculation
- trimming time mask
- CFC filter kernel and End Points extension
- `apply_filtering()` and `apply_filtering_with_derivatives()`
- HIC / 3ms / VC / Nij / femur calculation functions

Required verification:
- import compatibility for OFFSET and TRIMMING pages
- `capture-dir` after the move
- `compare-dir` against the Phase 5 baseline
- user startup, DATA OFFSET apply/reload, DATA TRIMMING apply/reload, and representative
  DATA FILTERING / INJURY entry test

## Phase 5-F viewer/channel search helper extraction
Implemented fourth extraction:

- new module: `app/services/preprocessing/channel_search.py`
- moved helpers:
  - `make_channel_search_text`
  - `infer_channel_group_key`
  - `find_resultant_or_axis`
  - `auto_detect_injury_channels`

Compatibility:
- `app/services/preprocessing/service.py` imports `make_channel_search_text`,
  `infer_channel_group_key`, and `auto_detect_injury_channels` from the new module.
- legacy private helper `_find_resultant_or_axis` remains available from `service.py` as
  an alias to `channel_search.find_resultant_or_axis`.

Not changed:
- channel matching semantics
- DATA FILTERING apply/commit functions
- CFC filter kernel and End Points extension
- HIC / 3ms / VC / Nij / femur calculation functions

Required verification:
- import compatibility for DATA FILTERING page
- `capture-dir` after the move
- `compare-dir` against the Phase 5 baseline
- user startup, DATA VIEWER channel list, DATA FILTERING channel search/grouping, and
  representative INJURY entry test

## Phase 5-G filter source helper extraction
Implemented fifth extraction:

- new module: `app/services/preprocessing/filter_sources.py`
- moved helpers:
  - `parse_cfc_filter_label`
  - `safe_columns_to_set`
  - `resolve_root_source_channel`
  - `extract_aligned_original_numeric_series`
  - `resolve_effective_time_column`
  - `resolve_filter_source_series`

Compatibility:
- `app/services/preprocessing/service.py` imports the moved helpers and preserves legacy names:
  - `parse_cfc_filter_label`
  - `_safe_columns_to_set`
  - `_resolve_root_source_channel`
  - `_extract_aligned_original_numeric_series`
  - `_resolve_effective_time_column`
  - `_resolve_filter_source_series`

Not changed:
- raw-aligned source selection semantics
- double-filtering prevention behavior
- `apply_filtering_with_derivatives()` orchestration body
- CFC filter kernel and End Points extension
- HIC / 3ms / VC / Nij / femur calculation functions

Required verification:
- import compatibility for injury and filtering pages
- `capture-dir` after the move
- `compare-dir` against the Phase 5 baseline
- user startup, DATA FILTERING apply/commit, AUTO SET, and representative INJURY entry test

## Phase 5-H-1 CFC/filtering kernel boundary review
Performed before moving any filtering kernel code.

Current CFC kernel owner:
- `app/services/preprocessing/service.py`
  - `_cfc_coefficients_sae_j211(fs, cfc_value)`
  - `_end_points_extend(y_segment, fs)`
  - `_apply_cfc_filter_segment(y_segment, fs, cfc_value)`
  - `apply_cfc_filter_to_series(time_arr, values, cfc_value)`

Active callers:
- Manual DATA FILTERING:
  - `app/ui/pages/filtering_page.py` calls `apply_filtering_with_derivatives()`.
  - `apply_filtering_with_derivatives()` first calls `apply_filtering()`.
  - `apply_filtering()` calls `_apply_cfc_filter_segment()` per contiguous valid group.
- DATA FILTERING injury-derived helper channels:
  - `apply_filtering_with_derivatives()` resolves raw-aligned source data through
    `filter_sources.resolve_filter_source_series()`.
  - required CFC helper channels are generated by calling `_apply_cfc_filter_segment()`
    against that resolved raw/source-aligned series.
  - if the selected manual filter already matches the required CFC, the redundant helper
    channel is removed instead of generated.
- Viewer preview filtering:
  - `app/ui/viewer_module.py` imports `_apply_cfc_filter_segment` as `cfc_filter_segment`
    and `_get_sample_rate` as `cfc_get_sample_rate`.
  - preview filtering keeps its own cache and contiguous-group loop, but the segment math
    still flows through the shared service kernel.
- Injury-prep filtering:
  - `app/ui/pages/injury_page.py` imports `apply_cfc_filter_to_series()` for raw-refiltered
    standard series when a required CFC is not already available.
  - `compute_neck_nij_metrics()` calls `apply_cfc_filter_to_series()` for Fz/My/Fx when
    internal CFC600 preparation is requested.
  - `compute_chest_metrics()` uses `apply_cfc_filter_to_series()` for VC target-CFC series
    only when the selected/pre-filtered source does not already match the target CFC.

Double-filtering guards currently in place:
- `filter_sources.resolve_filter_source_series()` traces derived channels back toward their
  root source and prefers raw-aligned source data when available.
- `apply_filtering_with_derivatives()` compares the manually selected CFC with each required
  derived CFC and removes the redundant derived channel when they match.
- `compute_chest_metrics()` uses selected CFC labels, prefiltered target-CFC displacement
  series, and raw displacement candidates before falling back to selected data.
- `injury_page.py` `_resolve_standard_series_for_calc()` prefers existing derived target-CFC
  channels, then selected/root channels already carrying the desired CFC label, then raw
  aligned data filtered once.

Do not move yet without a dedicated test slice:
- `_cfc_coefficients_sae_j211()` because coefficient math affects every CFC result.
- `_end_points_extend()` because it is the global End Points extension rule.
- `_apply_cfc_filter_segment()` because it is the common segment-level kernel.
- `apply_filtering_with_derivatives()` because it combines manual filtering, helper-channel
  routing, raw/source alignment, metadata writes, and double-filtering guards.
- `apply_cfc_filter_to_series()` because it is shared by injury-prep and neck/chest helpers.

Potential next slice:
- If approved, Phase 5-H-2 may move only the kernel functions into a small module such as
  `app/services/preprocessing/cfc_filter.py`, while keeping import aliases in `service.py`.
- Required checks before and after that move:
  - `py_compile` for `service.py`, `viewer_module.py`, `filtering_page.py`, `injury_page.py`
  - direct import compatibility for `_apply_cfc_filter_segment`, `apply_cfc_filter_to_series`,
    and `_get_sample_rate`
  - snapshot `capture-dir` / `compare-dir`
  - user tests: DATA VIEWER preview filter, DATA FILTERING manual apply/commit, AUTO SET,
    HEAD/CHEST/NECK injury entry, and saved `.pkl` reopen

## Phase 5-H-2 CFC kernel module extraction
Implemented with compatibility imports:

- new module: `app/services/preprocessing/cfc_filter.py`
- moved kernel functions and constants:
  - `FILTER_EXTENSION_MODE`
  - `_CFC_SF`
  - `cfc_coefficients_sae_j211`
  - `end_points_extend`
  - `apply_cfc_filter_segment`
  - `apply_cfc_filter_to_series`

Compatibility:
- `app/services/preprocessing/service.py` imports the moved functions and preserves legacy names:
  - `_cfc_coefficients_sae_j211`
  - `_end_points_extend`
  - `_apply_cfc_filter_segment`
  - `apply_cfc_filter_to_series`
  - `FILTER_EXTENSION_MODE`
- Existing imports from `service.py` remain valid for:
  - `app/ui/viewer_module.py`
  - `app/ui/pages/injury_page.py`
  - `app/ui/pages/filtering_page.py`
  - injury service modules

Not changed:
- SAE J211 coefficient math
- End Points extension behavior
- `filtfilt` arguments
- CFC class handling
- contiguous valid-group filtering behavior
- manual filtering orchestration
- derived-channel routing / double-filtering guards
- HIC / 3ms / VC / Nij / femur calculation functions

Required verification:
- `py_compile` for `cfc_filter.py`, `service.py`, `viewer_module.py`, `filtering_page.py`,
  and `injury_page.py`
- direct import compatibility for legacy names from `service.py`
- `capture-dir` after the move
- `compare-dir` against the Phase 5 baseline
- user tests: DATA VIEWER preview filter, DATA FILTERING manual apply/commit, AUTO SET,
  HEAD/CHEST/NECK injury entry, and saved `.pkl` reopen

## Phase 5-I-1 injury helper boundary review
Performed before moving any injury calculation helper code.

Current injury calculation owners still in `app/services/preprocessing/service.py`:
- HIC / 3ms helpers:
  - `_cumtrapz`
  - `_prepare_hic_series`
  - `_integral_at_query`
  - `_value_at_query`
  - `_update_best_hic`
  - `compute_hic_details`
  - `_level_exceedance_intervals`
  - `_clip_exceedance_detail`
  - `compute_3ms_one_peak_exceedance_details`
  - `_estimate_constant_dt`
  - `compute_3ms_multiple_peak_exceedance_details`
  - `compute_hic`
  - `compute_3ms_clip_details`
  - `compute_3ms_clip`
  - `compute_3ms_one_peak_details`
- Generic scalar helpers:
  - `_series_to_float`
  - `_convert_accel_to_g`
  - `compute_resultant_xyz`
  - `compute_nij`
  - `compute_nij_series`
  - `compute_injury_metrics`
- Neck helpers:
  - `build_neck_injury_channels`
  - `build_neck_injury_channel_metadata`
  - `compute_neck_nij_metrics`
- Chest helpers:
  - `_convert_accel_to_g_series`
  - `_convert_disp_to_mm_series`
  - `_pick_compression_positive`
  - `compute_chest_metrics`
  - nested VC/source-selection helpers inside `compute_chest_metrics`
- Femur helpers:
  - `_normalize_force_to_n`
  - `_peak_detail_abs`
  - `compute_femur_metrics`

Current callers:
- `app/services/injury/head_injury.py`
  - imports `compute_hic_details` from `service.py`.
  - imports `compute_3ms_bundle` from `app/services/injury/common_engines.py`.
- `app/services/injury/pelvis_injury.py`
  - imports `compute_resultant_xyz` from `service.py`.
  - imports `compute_3ms_bundle` from `common_engines.py`.
- `app/services/injury/chest_injury.py`
  - imports `compute_chest_metrics` from `service.py`.
- `app/services/injury/neck_injury.py`
  - imports `compute_neck_nij_metrics` from `service.py`.
- `app/services/injury/femur_injury.py`
  - imports `compute_femur_metrics` from `service.py`.
- `app/ui/pages/injury_page.py`
  - imports `compute_resultant_xyz`, `apply_cfc_filter_to_series`, and
    `parse_cfc_filter_label` from `service.py`.
  - resolves required-CFC standard series before calling injury service bundles.

Existing shared helper module:
- `app/services/injury/common_engines.py`
  - owns `compute_3ms_bundle()` and `compute_vc_engine_bundle()`.
  - imports 3ms detail functions lazily from `service.py` inside `compute_3ms_bundle()`.
  - has its own `_gradient_contiguous()` implementation for VC velocity.
- `compute_chest_metrics()` in `service.py` also has a nested `_gradient_contiguous()`
  style helper and calls `compute_vc_engine_bundle()`.
  This duplicate gradient area is calculation-sensitive and should not be collapsed in
  the same slice as a module move.

Do not move yet without dedicated snapshots and user tests:
- HIC / 3ms internals because they directly affect HEAD, CHEST, and PELVIS values.
- `compute_chest_metrics()` because it combines acceleration CFC selection, displacement
  target-CFC selection, V*C engine calls, VC display/regulatory output, and report payload
  keys.
- `compute_neck_nij_metrics()` because it combines unit normalization, optional internal
  CFC600 preparation, MOCy correction, Nij case calculation, and report metadata.
- `compute_femur_metrics()` because it combines unit normalization, absolute/signed peak
  semantics, and dummy limit pass/fail metadata.
- `compute_3ms_bundle()` / `compute_vc_engine_bundle()` consolidation because import order
  and duplicate helper behavior are part of the current compatibility surface.

Potential next safe slice:
- Phase 5-I-2 may move only small, pure, non-threshold helpers into a dedicated module while
  preserving `service.py` legacy import names. Candidate order:
  1. `compute_resultant_xyz`
  2. `_series_to_float`
  3. unit conversion helpers, but only after checking exact callers and snapshot output
- Keep HIC / 3ms / VC / Nij / femur formula bodies in place until each has a focused test
  slice and user confirmation.

Required verification for any Phase 5-I code move:
- `py_compile` for `service.py`, all `app/services/injury/*.py`, and `injury_page.py`
- direct import compatibility from `service.py`
- `capture-dir` and `compare-dir` against the Phase 5 baseline
- user tests:
  - HEAD HIC/3ms
  - CHEST 3ms/deflection/V*C
  - NECK force/moment/Nij
  - PELVIS resultant/3ms
  - FEMUR left/right force
  - REPORT SUMMARY and Excel export after injury results are saved
