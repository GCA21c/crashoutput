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
