import numpy as np
import pandas as pd

from app.core.isocode import rewrite_filter_code_in_text

from app.core.dummy import (
    NECK_DUMMY_PROFILES,
    CHEST_DUMMY_PROFILES,
    FEMUR_DUMMY_PROFILES,
    get_neck_dummy_profile,
    get_chest_dummy_profile,
    get_femur_dummy_profile,
)
from app.services.preprocessing.channel_roles import (
    _safe_text,
    detect_chest_channel_role,
    detect_femur_channel_role,
    detect_head_channel_role,
    detect_injury_channel_purpose_and_role,
    detect_neck_channel_role,
    derived_role_required_cfc,
    make_derived_channel_name,
    make_neck_derived_channel_name,
    neck_role_required_cfc,
)
from app.services.preprocessing.timing import (
    find_time0_row,
    get_numeric_channels,
    get_sample_rate as _get_sample_rate,
    get_time_numeric,
)
from app.services.preprocessing.offset import apply_offset, get_offset_sample_rows, trim_dataframe
from app.services.preprocessing.series_ops import replace_with_numeric_series as _replace_with_numeric_series
from app.services.preprocessing.channel_search import (
    auto_detect_injury_channels,
    find_resultant_or_axis as _find_resultant_or_axis,
    infer_channel_group_key,
    make_channel_search_text,
)
from app.services.preprocessing.filter_sources import (
    extract_aligned_original_numeric_series as _extract_aligned_original_numeric_series,
    parse_cfc_filter_label,
    resolve_effective_time_column as _resolve_effective_time_column,
    resolve_filter_source_series as _resolve_filter_source_series,
    resolve_root_source_channel as _resolve_root_source_channel,
    safe_columns_to_set as _safe_columns_to_set,
)
from app.services.preprocessing.cfc_filter import (
    FILTER_EXTENSION_MODE,
    apply_cfc_filter_segment as _apply_cfc_filter_segment,
    apply_cfc_filter_to_series,
    cfc_coefficients_sae_j211 as _cfc_coefficients_sae_j211,
    end_points_extend as _end_points_extend,
)
from app.services.injury.common_engines import compute_3ms_bundle, compute_vc_engine_bundle
from app.services.injury.chest_units import (
    convert_accel_to_g_series,
    convert_disp_to_mm_series,
    pick_compression_positive,
)
from app.services.injury.forces import normalize_force_to_n, peak_detail_abs
from app.services.injury.hic_3ms_math import (
    clip_exceedance_detail as _clip_exceedance_detail,
    compute_3ms_clip,
    compute_3ms_clip_details,
    compute_3ms_multiple_peak_exceedance_details,
    compute_3ms_one_peak_details,
    compute_3ms_one_peak_exceedance_details,
    compute_hic,
    compute_hic_details,
    cumtrapz as _cumtrapz,
    estimate_constant_dt as _estimate_constant_dt,
    integral_at_query as _integral_at_query,
    level_exceedance_intervals as _level_exceedance_intervals,
    prepare_hic_series as _prepare_hic_series,
    update_best_hic as _update_best_hic,
    value_at_query as _value_at_query,
)
from app.services.injury.legacy_metrics import compute_injury_metrics
from app.services.injury.neck_payloads import (
    build_neck_injury_channel_metadata,
    build_neck_injury_channels,
)
from app.services.injury.nij_math import compute_nij, compute_nij_series
from app.services.injury.scalars import convert_accel_to_g, series_to_float
from app.services.injury.vector_math import compute_resultant_xyz

FILTER_OPTIONS = ("Raw", "CFC 60", "CFC 180", "CFC 600", "CFC 1000")
OFFSET_SAMPLE_OPTIONS = (100, 300, 1000, 2000)


CHEST_CRITERIA_PRESETS = CHEST_DUMMY_PROFILES
NECK_CRITERIA_PRESETS = NECK_DUMMY_PROFILES
FEMUR_CRITERIA_PRESETS = FEMUR_DUMMY_PROFILES

def apply_filtering_with_derivatives(
    df,
    time_column,
    channel_to_filter,
    descriptions=None,
    units=None,
    existing_filter_labels=None,
    existing_derived_channels=None,
    existing_raw_map=None,
    original_df=None,
    original_time_column=None,
):
    out = apply_filtering(df, time_column, channel_to_filter)
    descriptions = dict(descriptions or {})
    units = dict(units or {})
    filter_labels = dict(existing_filter_labels or {})
    derived_channels = dict(existing_derived_channels or {})
    existing_raw_map = dict(existing_raw_map or {})

    x_all = get_time_numeric(out, time_column)
    fs = _get_sample_rate(x_all)

    # 과거 버전에서 생성된 HEAD injury 파생 채널은 더 이상 유지하지 않는다.
    # CHEST는 displacement CFC600 추적 채널만 유지하며, 그 외 chest injury 파생 채널은 정리한다.
    stale_injury_derived = [
        dch for dch, meta in list(derived_channels.items())
        if str((meta or {}).get("purpose") or "") == "head_injury"
        or (
            str((meta or {}).get("purpose") or "") == "chest_injury"
            and str((meta or {}).get("role") or "") != "disp"
        )
    ]
    for dch in stale_injury_derived:
        if dch in out.columns:
            out.drop(columns=[dch], inplace=True)
        descriptions.pop(dch, None)
        units.pop(dch, None)
        filter_labels.pop(dch, None)
        derived_channels.pop(dch, None)

    def _raw_source_channel_name(channel_name):
        root_channel = _resolve_root_source_channel(channel_name, derived_channels=derived_channels) or str(channel_name or '')
        if original_df is None:
            return root_channel
        original_columns = set(getattr(original_df, "columns", []))
        for candidate in (root_channel, channel_name):
            candidate = str(candidate or '').strip()
            if candidate and candidate in original_columns:
                return candidate
        raw_code = str(existing_raw_map.get(root_channel) or existing_raw_map.get(channel_name) or '').strip().upper()
        if raw_code:
            rewritten = str(rewrite_filter_code_in_text(root_channel or channel_name, 'Raw', raw_code=raw_code) or '').strip()
            if rewritten and rewritten in original_columns:
                return rewritten
        return root_channel

    for channel_name in channel_to_filter.keys():
        purpose, role = detect_injury_channel_purpose_and_role(
            channel_name,
            descriptions.get(channel_name, ""),
            units.get(channel_name, ""),
        )
        if purpose is None or role is None:
            continue

        resolved_source = _resolve_filter_source_series(
            df,
            time_column,
            channel_name,
            original_df=original_df,
            original_time_column=original_time_column,
            derived_channels=derived_channels,
        )
        raw_source_channel = str(
            (resolved_source or {}).get('root_source_channel')
            or _raw_source_channel_name(channel_name)
            or channel_name
        ).strip()
        raw_y = np.asarray((resolved_source or {}).get('values'), dtype=float)
        source_mode = str((resolved_source or {}).get('source_mode') or '').strip()
        created_from_raw = bool((resolved_source or {}).get('created_from_raw'))
        if raw_y.shape != x_all.shape and channel_name in df.columns:
            raw_y = pd.to_numeric(df[channel_name], errors="coerce").to_numpy(dtype=float)
            source_mode = 'current_channel_shape_fallback'
            created_from_raw = False
        valid = np.isfinite(x_all) & np.isfinite(raw_y)
        if not np.any(valid):
            continue

        idx = np.flatnonzero(valid)
        split_points = np.where(np.diff(idx) > 1)[0] + 1
        groups = np.split(idx, split_points)

        selected_filter_value = parse_cfc_filter_label(channel_to_filter.get(channel_name))
        for cfc_value in derived_role_required_cfc(purpose, role):
            derived_name = make_derived_channel_name(channel_name, purpose, role, cfc_value)
            if selected_filter_value == int(cfc_value):
                if derived_name in out.columns:
                    out.drop(columns=[derived_name], inplace=True)
                descriptions.pop(derived_name, None)
                units.pop(derived_name, None)
                filter_labels.pop(derived_name, None)
                derived_channels.pop(derived_name, None)
                continue
            filtered = raw_y.copy()
            for grp in groups:
                if grp.size < 8:
                    continue
                filtered[grp] = _apply_cfc_filter_segment(raw_y[grp].astype(float), fs, cfc_value)
            out[derived_name] = pd.Series(filtered, index=out.index, dtype=object)
            desc = (descriptions.get(channel_name) or str(channel_name)).strip()
            descriptions[derived_name] = f"{desc} [{purpose.replace('_', ' ').upper()} {role.upper()} CFC {int(cfc_value)}]"
            units[derived_name] = units.get(channel_name, "")
            filter_labels[derived_name] = f"CFC {int(cfc_value)}"
            derived_meta = {
                "source_channel": channel_name,
                "root_source_channel": raw_source_channel or channel_name,
                "role": role,
                "filter_label": f"CFC {int(cfc_value)}",
                "display_filter_label": f"CFC {int(cfc_value)}",
                "required_cfc": f"CFC {int(cfc_value)}",
                "cfc_value": int(cfc_value),
                "purpose": purpose,
                "filter_history": [{
                    "from_channel": raw_source_channel or channel_name,
                    "from_filter_label": "Raw",
                    "to_filter_label": f"CFC {int(cfc_value)}",
                    "raw_based": created_from_raw,
                    "extension_mode": FILTER_EXTENSION_MODE,
                    "purpose": purpose,
                    "role": role,
                    "source_mode": source_mode or None,
                }],
            }
            if purpose == "chest_injury" and role == "disp":
                derived_meta["created_from_raw"] = created_from_raw
                derived_meta["rebuild_policy"] = "raw_aligned_only"
            derived_channels[derived_name] = derived_meta

    return out, {
        "descriptions": descriptions,
        "units": units,
        "channel_filter_labels": filter_labels,
        "derived_channels": derived_channels,
    }


def apply_filtering(df, time_column, channel_to_filter):
    out = df.copy(deep=True)
    x_all = get_time_numeric(out, time_column)
    fs = _get_sample_rate(x_all)

    for channel_name, filter_label in channel_to_filter.items():
        if filter_label == "Raw":
            continue
        try:
            cfc_value = int(str(filter_label).replace("CFC", "").strip())
        except Exception:
            continue

        raw_y = pd.to_numeric(out[channel_name], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(x_all) & np.isfinite(raw_y)
        if not np.any(valid):
            continue

        filtered = raw_y.copy()
        idx = np.flatnonzero(valid)
        split_points = np.where(np.diff(idx) > 1)[0] + 1
        groups = np.split(idx, split_points)
        for grp in groups:
            if grp.size < 8:
                continue
            filtered[grp] = _apply_cfc_filter_segment(raw_y[grp].astype(float), fs, cfc_value)

        _replace_with_numeric_series(out, channel_name, filtered)

    return out


_series_to_float = series_to_float


_convert_accel_to_g = convert_accel_to_g


def compute_neck_nij_metrics(time_s, fz_n, my_nm, apply_cfc600=True, criterion_key="H3_50%M", fz_unit=None, my_unit=None, fx_n=None, fx_unit=None, moment_is_mocy=False, fz_peak_n=None):
    """Compute Nij from upper neck Fz and MOCy.

    According to the crash criteria reference, Nij uses upper-neck Force Z
    filtered at CFC 600 together with the total moment about the occipital
    condyle (MOCy). For upper load cells this is derived from the filtered raw
    My and Fx channels using the dummy/load-cell lever arm D:

        MOCy = My + Fx * D

    If Fx is not available, the function falls back to raw My and reports that
    MOC correction was not applied.
    """
    time_arr = np.asarray(time_s, dtype=float)
    fz = np.asarray(fz_n, dtype=float)
    my = np.asarray(my_nm, dtype=float)
    fx = None if fx_n is None else np.asarray(fx_n, dtype=float)

    fz_unit_text = str(fz_unit or '').strip()
    my_unit_text = str(my_unit or '').strip()
    fx_unit_text = str(fx_unit or '').strip()

    # Normalize common engineering units to the convention used by Nij:
    # axial force in N and bending moment in Nm.
    fz_unit_l = fz_unit_text.lower().replace('·', '').replace('*', '').replace(' ', '')
    my_unit_l = my_unit_text.lower().replace('·', '').replace('*', '').replace(' ', '')

    if fz_unit_l in ('kn', 'kilonewton', 'kilonewtons'):
        fz = fz * 1000.0
        fz_unit_text = 'N'
    elif fz_unit_l in ('mn',):
        fz = fz * 1_000_000.0
        fz_unit_text = 'N'

    if my_unit_l in ('nmm', 'nmm.', 'n-mm', 'n/mm', 'newtonmillimeter', 'newtonmillimeters'):
        my = my / 1000.0
        my_unit_text = 'Nm'
    elif my_unit_l in ('knm', 'k nm', 'kn-m', 'kilonewtonmeter', 'kilonewtonmeters'):
        my = my * 1000.0
        my_unit_text = 'Nm'

    if fx is not None:
        fx_unit_l = fx_unit_text.lower().replace('·', '').replace('*', '').replace(' ', '')
        if fx_unit_l in ('kn', 'kilonewton', 'kilonewtons'):
            fx = fx * 1000.0
            fx_unit_text = 'N'
        elif fx_unit_l in ('mn',):
            fx = fx * 1_000_000.0
            fx_unit_text = 'N'

    preset_key = str(criterion_key or "H3_50%M")
    limits = get_neck_dummy_profile(preset_key)

    if apply_cfc600:
        fz = apply_cfc_filter_to_series(time_arr, fz, 600)
        my = apply_cfc_filter_to_series(time_arr, my, 600)
        if fx is not None:
            fx = apply_cfc_filter_to_series(time_arr, fx, 600)

    peak_force = np.asarray(fz_peak_n if fz_peak_n is not None else fz, dtype=float)

    moc_d = float(limits.get('moc_d', 0.0) or 0.0)
    resolved_load_cell_type = 'Preset D'
    my_source = my.copy()
    if moment_is_mocy:
        moc_applied = True
    else:
        moc_applied = fx is not None and np.isfinite(fx).any() and abs(moc_d) > 0.0
        if moc_applied:
            my = my + fx * moc_d

    # Nij case calculation needs both Fz and MOCy to be valid at the same sample.
    # However peak Fz / peak My summaries are properties of the individual
    # input channels, so they must not be restricted by the joint-valid mask used for Nij.
    valid = np.isfinite(time_arr) & np.isfinite(fz) & np.isfinite(my)
    if not np.any(valid):
        return None

    valid_idx = np.flatnonzero(valid)
    tv = time_arr[valid]
    fzv = fz[valid]
    myv = my[valid]

    force_valid = np.isfinite(time_arr) & np.isfinite(peak_force)
    moment_valid = np.isfinite(time_arr) & np.isfinite(my)
    fv_t = time_arr[force_valid]
    fv_fz = peak_force[force_valid]
    mv_t = time_arr[moment_valid]
    mv_my = my[moment_valid]

    ntf = np.full_like(fz, np.nan, dtype=float)
    nte = np.full_like(fz, np.nan, dtype=float)
    ncf = np.full_like(fz, np.nan, dtype=float)
    nce = np.full_like(fz, np.nan, dtype=float)
    nij = np.full_like(fz, np.nan, dtype=float)

    tf_mask_v = (fzv > 0.0) & (myv > 0.0)
    te_mask_v = (fzv > 0.0) & (myv < 0.0)
    cf_mask_v = (fzv < 0.0) & (myv > 0.0)
    ce_mask_v = (fzv < 0.0) & (myv < 0.0)

    # The NIJ case rule uses an AND condition for each case.
    # If the force/moment sign pair does not match a case, that case is zero.
    # For compression and extension, the critical values are negative in the
    # published convention so that Fz/Fzc and My/MyE still produce positive Nij.
    fzt = float(limits['Fzt'])
    fzc = -abs(float(limits['Fzc']))
    myf = float(limits['MyF'])
    mye = -abs(float(limits['MyE']))

    ntf_v = np.zeros_like(fzv, dtype=float)
    nte_v = np.zeros_like(fzv, dtype=float)
    ncf_v = np.zeros_like(fzv, dtype=float)
    nce_v = np.zeros_like(fzv, dtype=float)
    nij_v = np.zeros_like(fzv, dtype=float)
    mode_v = np.full(fzv.shape, '', dtype=object)

    if np.any(tf_mask_v):
        val = (fzv[tf_mask_v] / fzt) + (myv[tf_mask_v] / myf)
        ntf_v[tf_mask_v] = val
        nij_v[tf_mask_v] = val
        mode_v[tf_mask_v] = 'NTF'
    if np.any(te_mask_v):
        val = (fzv[te_mask_v] / fzt) + (myv[te_mask_v] / mye)
        nte_v[te_mask_v] = val
        nij_v[te_mask_v] = val
        mode_v[te_mask_v] = 'NTE'
    if np.any(cf_mask_v):
        val = (fzv[cf_mask_v] / fzc) + (myv[cf_mask_v] / myf)
        ncf_v[cf_mask_v] = val
        nij_v[cf_mask_v] = val
        mode_v[cf_mask_v] = 'NCF'
    if np.any(ce_mask_v):
        val = (fzv[ce_mask_v] / fzc) + (myv[ce_mask_v] / mye)
        nce_v[ce_mask_v] = val
        nij_v[ce_mask_v] = val
        mode_v[ce_mask_v] = 'NCE'

    ntf[valid] = ntf_v
    nte[valid] = nte_v
    ncf[valid] = ncf_v
    nce[valid] = nce_v
    nij[valid] = nij_v

    case_label_full = np.full(time_arr.shape, '', dtype=object)
    case_label_full[valid] = mode_v

    def _global_extreme_idx(arr, mode='max'):
        arr = np.asarray(arr, dtype=float)
        finite = np.isfinite(arr)
        if not np.any(finite):
            return None
        finite_idx = np.flatnonzero(finite)
        arr_f = arr[finite]
        target = np.nanmax(arr_f) if mode == 'max' else np.nanmin(arr_f)
        cand = np.flatnonzero(np.isclose(arr_f, target, rtol=1e-12, atol=1e-12))
        return int(finite_idx[cand[-1]]) if cand.size else int(finite_idx[-1])

    def _global_peak_value(arr, mode='max'):
        idx = _global_extreme_idx(arr, mode)
        return None if idx is None else float(np.asarray(arr, dtype=float)[idx])

    peak_tension_idx = _global_extreme_idx(fv_fz, 'max')
    peak_compression_idx = _global_extreme_idx(fv_fz, 'min')
    peak_flexion_idx = _global_extreme_idx(mv_my, 'max')
    peak_extension_idx = _global_extreme_idx(mv_my, 'min')
    peak_tension_val = _global_peak_value(fv_fz, 'max')
    peak_compression_val = _global_peak_value(fv_fz, 'min')
    peak_flexion_val = _global_peak_value(mv_my, 'max')
    peak_extension_val = _global_peak_value(mv_my, 'min')

    peak_ntf_idx = _global_extreme_idx(ntf_v, 'max')
    peak_nte_idx = _global_extreme_idx(nte_v, 'max')
    peak_ncf_idx = _global_extreme_idx(ncf_v, 'max')
    peak_nce_idx = _global_extreme_idx(nce_v, 'max')
    peak_overall_idx = _global_extreme_idx(nij_v, 'max')
    peak_overall = _global_peak_value(nij_v, 'max')
    dominant_mode = mode_v[peak_overall_idx] if peak_overall_idx is not None and mode_v.size else '-'

    joint_peak_tension_idx = _global_extreme_idx(fzv, 'max')
    joint_peak_compression_idx = _global_extreme_idx(fzv, 'min')
    joint_peak_tension_val = _global_peak_value(fzv, 'max')
    joint_peak_compression_val = _global_peak_value(fzv, 'min')

    metrics = {
        'time': time_arr,
        'valid_index': valid_idx,
        'fz_filtered': peak_force,
        'fz_peak_filtered': peak_force,
        'fz_nij_filtered': fz,
        'my_raw_filtered': my_source,
        'my_filtered': my,
        'fx_filtered': fx if fx is not None else None,
        'ntf': ntf,
        'nte': nte,
        'ncf': ncf,
        'nce': nce,
        'nij': nij,
        'case_label': case_label_full,
        'peak_tension_fz': peak_tension_val,
        'peak_compression_fz_raw': peak_compression_val,
        'peak_compression_fz': (abs(peak_compression_val) if peak_compression_val is not None else None),
        'joint_peak_tension_fz': joint_peak_tension_val,
        'joint_peak_compression_fz_raw': joint_peak_compression_val,
        'joint_peak_compression_fz': (abs(joint_peak_compression_val) if joint_peak_compression_val is not None else None),
        'peak_flexion_my': peak_flexion_val,
        'peak_extension_my': peak_extension_val,
        'peak_tension_idx_force_valid': peak_tension_idx,
        'peak_compression_idx_force_valid': peak_compression_idx,
        'peak_flexion_idx_moment_valid': peak_flexion_idx,
        'peak_extension_idx_moment_valid': peak_extension_idx,
        'peak_tension_idx': int(np.flatnonzero(force_valid)[peak_tension_idx]) if peak_tension_idx is not None else None,
        'peak_compression_idx': int(np.flatnonzero(force_valid)[peak_compression_idx]) if peak_compression_idx is not None else None,
        'joint_peak_tension_idx': int(valid_idx[joint_peak_tension_idx]) if joint_peak_tension_idx is not None else None,
        'joint_peak_compression_idx': int(valid_idx[joint_peak_compression_idx]) if joint_peak_compression_idx is not None else None,
        'peak_flexion_idx': int(np.flatnonzero(moment_valid)[peak_flexion_idx]) if peak_flexion_idx is not None else None,
        'peak_extension_idx': int(np.flatnonzero(moment_valid)[peak_extension_idx]) if peak_extension_idx is not None else None,
        'peak_tension_time': float(fv_t[peak_tension_idx]) if peak_tension_idx is not None else None,
        'peak_compression_time': float(fv_t[peak_compression_idx]) if peak_compression_idx is not None else None,
        'joint_peak_tension_time': float(tv[joint_peak_tension_idx]) if joint_peak_tension_idx is not None else None,
        'joint_peak_compression_time': float(tv[joint_peak_compression_idx]) if joint_peak_compression_idx is not None else None,
        'peak_flexion_time': float(mv_t[peak_flexion_idx]) if peak_flexion_idx is not None else None,
        'peak_extension_time': float(mv_t[peak_extension_idx]) if peak_extension_idx is not None else None,
        'peak_ntf': _global_peak_value(ntf_v, 'max'),
        'peak_nte': _global_peak_value(nte_v, 'max'),
        'peak_ncf': _global_peak_value(ncf_v, 'max'),
        'peak_nce': _global_peak_value(nce_v, 'max'),
        'peak_ntf_idx_valid': peak_ntf_idx,
        'peak_nte_idx_valid': peak_nte_idx,
        'peak_ncf_idx_valid': peak_ncf_idx,
        'peak_nce_idx_valid': peak_nce_idx,
        'peak_ntf_time': float(tv[peak_ntf_idx]) if peak_ntf_idx is not None else None,
        'peak_nte_time': float(tv[peak_nte_idx]) if peak_nte_idx is not None else None,
        'peak_ncf_time': float(tv[peak_ncf_idx]) if peak_ncf_idx is not None else None,
        'peak_nce_time': float(tv[peak_nce_idx]) if peak_nce_idx is not None else None,
        'overall_nij': peak_overall,
        'overall_nij_idx_valid': peak_overall_idx,
        'overall_nij_idx': int(valid_idx[peak_overall_idx]) if peak_overall_idx is not None else None,
        'overall_nij_time': float(tv[peak_overall_idx]) if peak_overall_idx is not None else None,
        'dominant_mode': dominant_mode,
        'criteria': {
            'criterion_key': preset_key,
            'criterion_label': limits.get('label', preset_key),
            'dummy_family': limits.get('dummy_family', '-'),
            'source': limits.get('source', '-'),
            'input_force': 'Fz',
            'input_moment': 'MOCy' if (moc_applied or moment_is_mocy) else 'My',
            'f_tension_crit': limits['Fzt'],
            'f_compression_crit': -abs(limits['Fzc']),
            'm_flexion_crit': limits['MyF'],
            'm_extension_crit': -abs(limits['MyE']),
            'filter': 'CFC 600' if apply_cfc600 else 'Raw',
            'peak_tension_limit': limits.get('peak_tension_limit'),
            'peak_compression_limit': limits.get('peak_compression_limit'),
            'peak_rule': 'global extrema on individual source channel validity (Fz or MOCy)',
            'input_force_unit': fz_unit_text or None,
            'input_moment_unit': my_unit_text or None,
            'input_fx_unit': fx_unit_text or None,
            'moc_d': moc_d,
            'moc_applied': moc_applied,
            'moment_is_mocy': bool(moment_is_mocy),
            'load_cell_type': resolved_load_cell_type,
        }
    }
    return metrics



_convert_accel_to_g_series = convert_accel_to_g_series


_convert_disp_to_mm_series = convert_disp_to_mm_series


_pick_compression_positive = pick_compression_positive


def compute_chest_metrics(
    time_s,
    ax,
    ay,
    az,
    displacement,
    accel_units=None,
    disp_unit=None,
    criterion_key='H3_50%M',
    raw_displacement=None,
    raw_accel=None,
    accel_filter_labels=None,
    disp_filter_label=None,
    disp_prefiltered=None,
    vc_sign_pref=1.0,
    use_high_res_cumulative_3ms=True,
):
    t = np.asarray(time_s, dtype=float)

    def _raw_length_ok(candidate):
        return candidate is not None and np.asarray(candidate).shape == np.asarray(t).shape

    def _series_for_target_cfc(selected_values, raw_values, unit_text, selected_filter_label, target_cfc, convert_fn):
        selected_arr = np.asarray(convert_fn(selected_values, unit_text), dtype=float)
        raw_arr = None
        if _raw_length_ok(raw_values):
            raw_arr = np.asarray(convert_fn(raw_values, unit_text), dtype=float)

        selected_cfc = parse_cfc_filter_label(selected_filter_label)
        if selected_cfc == int(target_cfc):
            return selected_arr, {
                'source': 'selected',
                'selected_cfc': selected_cfc,
                'target_cfc': int(target_cfc),
                'double_filtered': False,
            }

        if raw_arr is not None:
            filtered = np.asarray(apply_cfc_filter_to_series(t, raw_arr, int(target_cfc)), dtype=float)
            return filtered, {
                'source': 'raw_refiltered',
                'selected_cfc': selected_cfc,
                'target_cfc': int(target_cfc),
                'double_filtered': False,
            }

        if selected_cfc is None:
            filtered = np.asarray(apply_cfc_filter_to_series(t, selected_arr, int(target_cfc)), dtype=float)
            return filtered, {
                'source': 'selected_refiltered',
                'selected_cfc': selected_cfc,
                'target_cfc': int(target_cfc),
                'double_filtered': False,
            }

        return selected_arr, {
            'source': 'selected_fallback',
            'selected_cfc': selected_cfc,
            'target_cfc': int(target_cfc),
            'double_filtered': True,
        }

    def _disp_series_for_target_cfc(selected_values, raw_values, unit_text, selected_filter_label, target_cfc):
        selected_arr = np.asarray(_convert_disp_to_mm_series(selected_values, unit_text), dtype=float)
        raw_arr = None
        if _raw_length_ok(raw_values):
            raw_arr = np.asarray(_convert_disp_to_mm_series(raw_values, unit_text), dtype=float)

        selected_cfc = parse_cfc_filter_label(selected_filter_label)
        target_cfc = int(target_cfc)

        if selected_cfc == target_cfc:
            return selected_arr, {
                'source': 'selected',
                'selected_cfc': selected_cfc,
                'target_cfc': target_cfc,
                'double_filtered': False,
            }

        pref_arr = disp_prefiltered.get(target_cfc)
        if pref_arr is not None and np.asarray(pref_arr).shape == np.asarray(t).shape:
            return np.asarray(_convert_disp_to_mm_series(pref_arr, unit_text), dtype=float), {
                'source': 'prefiltered_target',
                'selected_cfc': selected_cfc,
                'target_cfc': target_cfc,
                'double_filtered': False,
            }

        if raw_arr is not None:
            filtered = np.asarray(apply_cfc_filter_to_series(t, raw_arr, target_cfc), dtype=float)
            return filtered, {
                'source': 'raw_refiltered',
                'selected_cfc': selected_cfc,
                'target_cfc': target_cfc,
                'double_filtered': False,
            }

        return selected_arr, {
            'source': 'selected_fallback',
            'selected_cfc': selected_cfc,
            'target_cfc': target_cfc,
            'double_filtered': selected_cfc is not None and selected_cfc != target_cfc,
        }

    raw_accel = dict(raw_accel or {})
    accel_filter_labels = dict(accel_filter_labels or {})
    disp_prefiltered = {int(k): np.asarray(v, dtype=float) for k, v in dict(disp_prefiltered or {}).items() if v is not None}

    xg, x_meta = _series_for_target_cfc(ax, raw_accel.get('x'), (accel_units or {}).get('x', ''), accel_filter_labels.get('x'), 180, _convert_accel_to_g_series)
    yg, y_meta = _series_for_target_cfc(ay, raw_accel.get('y'), (accel_units or {}).get('y', ''), accel_filter_labels.get('y'), 180, _convert_accel_to_g_series)
    zg, z_meta = _series_for_target_cfc(az, raw_accel.get('z'), (accel_units or {}).get('z', ''), accel_filter_labels.get('z'), 180, _convert_accel_to_g_series)

    disp_selected_mm = np.asarray(_convert_disp_to_mm_series(displacement, disp_unit or ''), dtype=float)
    raw_disp_candidate_mm = _convert_disp_to_mm_series(
        raw_displacement if raw_displacement is not None else displacement,
        disp_unit or ''
    )
    raw_length_ok = np.asarray(raw_disp_candidate_mm).shape == np.asarray(t).shape
    raw_disp_mm = np.asarray(raw_disp_candidate_mm if raw_length_ok else disp_selected_mm, dtype=float)

    # UI/display displacement follows the current selected preprocessing result as-is.
    # VC mode-specific filtering is handled separately from the raw-aligned source to avoid
    # accidental CFC180->CFC600 or CFC600->CFC180 double processing.
    disp_plot_mm = disp_selected_mm
    disp_ece_mm, disp_ece_meta = _disp_series_for_target_cfc(displacement, raw_displacement, disp_unit or '', disp_filter_label, 180)
    disp_sae_mm, disp_sae_meta = _disp_series_for_target_cfc(displacement, raw_displacement, disp_unit or '', disp_filter_label, 600)

    res_g = compute_resultant_xyz(xg, yg, zg)
    preset = get_chest_dummy_profile(str(criterion_key))

    axis_clip_details = {
        'x': compute_3ms_clip_details(t, xg, use_abs=True),
        'y': compute_3ms_clip_details(t, yg, use_abs=True),
        'z': compute_3ms_clip_details(t, zg, use_abs=True),
    }
    peak_3ms_bundle = compute_3ms_bundle(
        t,
        res_g,
        use_abs=True,
        include_res_peak=True,
        use_high_res_cumulative_3ms=use_high_res_cumulative_3ms,
    )
    one_peak_detail = dict(peak_3ms_bundle.get('one_peak_3ms', {}))
    one_peak_detail['axis'] = None
    res_clip_detail = dict(peak_3ms_bundle.get('multiple_peak_3ms', {}))
    resultant_peak = peak_3ms_bundle.get('res_peak')


    def _gradient_contiguous(time_arr, values, method='gradient'):
        time_arr = np.asarray(time_arr, dtype=float)
        values = np.asarray(values, dtype=float)
        out = np.full_like(values, np.nan, dtype=float)
        valid = np.isfinite(time_arr) & np.isfinite(values)
        if not np.any(valid):
            return out
        idx = np.flatnonzero(valid)
        split_points = np.where(np.diff(idx) > 1)[0] + 1
        groups = np.split(idx, split_points)
        for grp in groups:
            if grp.size < 3:
                continue
            seg_t = time_arr[grp]
            seg_y = values[grp]
            dt = np.diff(seg_t)
            uniform = dt.size > 0 and np.all(np.isfinite(dt)) and np.all(dt > 0) and np.allclose(dt, np.median(dt), rtol=1e-6, atol=1e-12)
            if method == 'five_point' and grp.size >= 5 and uniform:
                h = float(np.median(dt))
                grad = np.full_like(seg_y, np.nan, dtype=float)
                grad[2:-2] = (-seg_y[4:] + 8.0 * seg_y[3:-1] - 8.0 * seg_y[1:-3] + seg_y[:-4]) / (12.0 * h)
                grad[0] = (-25.0 * seg_y[0] + 48.0 * seg_y[1] - 36.0 * seg_y[2] + 16.0 * seg_y[3] - 3.0 * seg_y[4]) / (12.0 * h)
                grad[1] = (-3.0 * seg_y[0] - 10.0 * seg_y[1] + 18.0 * seg_y[2] - 6.0 * seg_y[3] + seg_y[4]) / (12.0 * h)
                grad[-2] = (3.0 * seg_y[-1] + 10.0 * seg_y[-2] - 18.0 * seg_y[-3] + 6.0 * seg_y[-4] - seg_y[-5]) / (12.0 * h)
                grad[-1] = (25.0 * seg_y[-1] - 48.0 * seg_y[-2] + 36.0 * seg_y[-3] - 16.0 * seg_y[-4] + 3.0 * seg_y[-5]) / (12.0 * h)
            else:
                grad = np.gradient(seg_y, seg_t, edge_order=2)
                grad[0] = grad[1]
                grad[-1] = grad[-2]
            out[grp] = grad
        return out

    def _suppress_edge_pulse(series):
        arr = np.asarray(series, dtype=float).copy()
        finite_idx = np.flatnonzero(np.isfinite(arr))
        if finite_idx.size >= 3:
            arr[finite_idx[0]] = arr[finite_idx[1]]
            arr[finite_idx[-1]] = arr[finite_idx[-2]]
        return arr

    def _extrema_times(series):
        arr = np.asarray(series, dtype=float)
        mask = np.isfinite(t) & np.isfinite(arr)
        if not np.any(mask):
            return None, None
        tv = t[mask]
        sv = arr[mask]
        return float(tv[int(np.nanargmax(sv))]), float(tv[int(np.nanargmin(sv))])

    def _refine_peak_info(series, mode='max'):
        arr = np.asarray(series, dtype=float)
        mask = np.isfinite(t) & np.isfinite(arr)
        if not np.any(mask):
            return {'value': None, 'time_s': None, 'index': None}
        valid_idx = np.flatnonzero(mask)
        valid_arr = arr[valid_idx]
        idx_local = int(np.nanargmax(valid_arr) if mode == 'max' else np.nanargmin(valid_arr))
        idx = int(valid_idx[idx_local])
        if idx <= 0 or idx >= len(arr) - 1:
            return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}
        y0, y1, y2 = arr[idx - 1], arr[idx], arr[idx + 1]
        x0, x1, x2 = t[idx - 1], t[idx], t[idx + 1]
        if not all(np.isfinite(v) for v in (y0, y1, y2, x0, x1, x2)):
            return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}
        dt1 = x1 - x0
        dt2 = x2 - x1
        if dt1 <= 0 or dt2 <= 0 or not np.isclose(dt1, dt2, rtol=1e-6, atol=1e-12):
            return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}
        h = float((dt1 + dt2) * 0.5)
        denom = (y0 - 2.0 * y1 + y2)
        if abs(denom) < 1e-18:
            return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}
        delta = 0.5 * (y0 - y2) / denom
        if not np.isfinite(delta) or abs(delta) > 1.0:
            return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}
        peak_time = float(x1 + delta * h)
        peak_value = float(y1 - 0.25 * (y0 - y2) * delta)
        return {'value': peak_value, 'time_s': peak_time, 'index': idx}


    def _representative_vc_peak(series, mode='max', cluster_window_s=0.020, close_ratio=0.97):
        # Readout helper only: keep the underlying VC formula unchanged.
        # When two or more nearby extrema are almost equal, prefer the later one
        # in the same event cluster. This improves stability against small
        # derivative/filter differences without changing the VC signal itself.
        arr = np.asarray(series, dtype=float)
        mask = np.isfinite(t) & np.isfinite(arr)
        if not np.any(mask):
            return {'value': None, 'time_s': None, 'index': None}
        valid_idx = np.flatnonzero(mask)
        a = arr[valid_idx]
        if a.size < 3:
            idx = int(valid_idx[int(np.nanargmax(a) if mode == 'max' else np.nanargmin(a))])
            return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}

        if mode == 'max':
            peak_mask = (a[1:-1] >= a[:-2]) & (a[1:-1] >= a[2:])
            cand = valid_idx[1:-1][peak_mask & np.isfinite(a[1:-1])]
            if cand.size == 0:
                return _refine_peak_info(arr, mode='max')
            global_peak = float(np.nanmax(arr[mask]))
            threshold = global_peak * float(close_ratio)
            cand = cand[arr[cand] >= threshold]
        else:
            peak_mask = (a[1:-1] <= a[:-2]) & (a[1:-1] <= a[2:])
            cand = valid_idx[1:-1][peak_mask & np.isfinite(a[1:-1])]
            if cand.size == 0:
                return _refine_peak_info(arr, mode='min')
            global_peak = float(np.nanmin(arr[mask]))
            threshold = global_peak * float(close_ratio)
            cand = cand[arr[cand] <= threshold]

        if cand.size == 0:
            return _refine_peak_info(arr, mode=mode)

        cand = np.sort(cand)
        # build clusters of nearby extrema
        clusters = [[int(cand[0])]]
        for idx in cand[1:]:
            if (t[int(idx)] - t[clusters[-1][-1]]) <= float(cluster_window_s):
                clusters[-1].append(int(idx))
            else:
                clusters.append([int(idx)])

        # choose the cluster with the strongest absolute representative amplitude
        def cluster_score(cluster):
            vals = np.asarray([arr[i] for i in cluster], dtype=float)
            return float(np.nanmax(vals)) if mode == 'max' else float(np.abs(np.nanmin(vals)))

        best_cluster = max(clusters, key=cluster_score)
        chosen = int(best_cluster[-1])  # prefer later representative in the same event
        return {'value': float(arr[chosen]), 'time_s': float(t[chosen]), 'index': chosen}

    def _compute_vc_mode(disp_source_mm, mode, filter_meta=None):
        disp_source_mm = np.asarray(disp_source_mm, dtype=float)
        sign_pref = 1.0
        display_mode = 'strict'
        bundle = compute_vc_engine_bundle(
            t,
            disp_source_mm,
            preset,
            sign_pref=float(vc_sign_pref),
            filter_meta=filter_meta,
            display_mode=display_mode,
            user_direction_mode=True,
        )
        bundle['peak_method'] = display_mode
        return bundle

    # Use the pre-processing result directly when it already matches the criterion filter class.
    # Otherwise rebuild the required CFC channel from the original/raw displacement once so the
    # injury calculation does not double-filter an already processed channel.
    vc_sae_bundle = _compute_vc_mode(disp_sae_mm, 'SAE_J1727', disp_sae_meta)
    vc_ece_bundle = _compute_vc_mode(disp_ece_mm, 'ECE_94', disp_ece_meta)
    disp_sae_mm = vc_sae_bundle['disp_filtered_mm']
    vel_sae_mps = vc_sae_bundle['vel_regulatory_mps']
    sae_vc = vc_sae_bundle['vc_regulatory']
    sae_vc_display = vc_sae_bundle['vc_display']
    sign_sae = vc_sae_bundle['sign']
    disp_ece_mm = vc_ece_bundle['disp_filtered_mm']
    vel_ece_mps = vc_ece_bundle['vel_regulatory_mps']
    ece_vc = vc_ece_bundle['vc_regulatory']
    ece_vc_display = vc_ece_bundle['vc_display']
    sign_ece = vc_ece_bundle['sign']

    def _peak_info(series, use_abs=False, return_abs_value=False):
        arr = np.asarray(series, dtype=float)
        mask = np.isfinite(t) & np.isfinite(arr)
        if not np.any(mask):
            return {'value': None, 'time_s': None, 'index': None}
        arr_eval = np.abs(arr[mask]) if use_abs else arr[mask]
        idx_local = int(np.nanargmax(arr_eval))
        idx = int(np.flatnonzero(mask)[idx_local])
        value = float(abs(arr[idx])) if return_abs_value else float(arr[idx])
        return {'value': value, 'time_s': float(t[idx]), 'index': idx}

    vc_ece_clip_detail = compute_3ms_clip_details(t, ece_vc, use_abs=True)
    vc_sae_clip_detail = compute_3ms_clip_details(t, sae_vc, use_abs=True)
    disp_filter_note = (
        'CHEST preprocessing guideline: acceleration uses CFC180. Display/reference chest displacement may exist as preprocessing output. '
        'For V*C, SAE J1727 uses CFC600 displacement and ECE-R94 uses CFC180 displacement. '
        'Whenever the selected displacement channel does not already match the required CFC class, the code rebuilds the missing path from raw-aligned displacement to avoid double filtering.'
    )
    if disp_sae_meta.get('source') == 'raw_refiltered' and disp_ece_meta.get('source') == 'selected':
        disp_filter_note += ' Selected displacement was treated as the CFC180 path, and SAE J1727 was rebuilt from raw-aligned displacement at CFC600.'
    elif disp_ece_meta.get('source') == 'raw_refiltered' and disp_sae_meta.get('source') == 'selected':
        disp_filter_note += ' Selected displacement was treated as the CFC600 path, and ECE-R94 was rebuilt from raw-aligned displacement at CFC180.'
    elif disp_sae_meta.get('double_filtered') or disp_ece_meta.get('double_filtered'):
        disp_filter_note += ' Raw-aligned displacement was unavailable, so the selected displacement channel was reused as-is for the unmatched VC path to avoid double filtering.'
    elif not raw_length_ok:
        disp_filter_note += ' Original displacement length did not match the current trimmed dataset, so raw-aligned rebuilding was skipped.'

    return {
        'criteria': preset,
        'time': t,
        'x_g': np.asarray(xg, dtype=float),
        'y_g': np.asarray(yg, dtype=float),
        'z_g': np.asarray(zg, dtype=float),
        'resultant_g': np.asarray(res_g, dtype=float),
        'axis_3ms_details': axis_clip_details,
        'one_peak_3ms_detail': one_peak_detail,
        'one_peak_3ms_g': one_peak_detail.get('value'),
        'multiple_peak_3ms_detail': res_clip_detail,
        'multiple_peak_3ms_g': res_clip_detail.get('value'),
        'peak_3ms_bundle': peak_3ms_bundle,
        'resultant_peak': resultant_peak if resultant_peak is not None else _peak_info(res_g, use_abs=False),
        'displacement_mm': np.asarray(disp_plot_mm, dtype=float),
        'displacement_raw_mm': np.asarray(raw_disp_mm, dtype=float),
        'displacement_sae_cfc600_mm': np.asarray(disp_sae_mm, dtype=float),
        'displacement_peak': _peak_info(disp_plot_mm, use_abs=True, return_abs_value=True),
        'velocity_mps': np.asarray(vel_ece_mps, dtype=float),
        'velocity_sae_mps': np.asarray(vel_sae_mps, dtype=float),
        'vc_ece': np.asarray(ece_vc, dtype=float),
        'vc_sae': np.asarray(sae_vc, dtype=float),
        'vc_ece_display': np.asarray(ece_vc_display, dtype=float),
        'vc_sae_display': np.asarray(sae_vc_display, dtype=float),
        'vc_ece_peak': _peak_info(ece_vc, use_abs=True, return_abs_value=True),
        'vc_sae_peak': _peak_info(sae_vc, use_abs=True, return_abs_value=True),
        'vc_ece_max_regulatory': dict(vc_ece_bundle.get('regulatory_max') or {}),
        'vc_ece_min_regulatory': dict(vc_ece_bundle.get('regulatory_min') or {}),
        'vc_sae_max_regulatory': dict(vc_sae_bundle.get('regulatory_max') or {}),
        'vc_sae_min_regulatory': dict(vc_sae_bundle.get('regulatory_min') or {}),
        'vc_ece_max_display': dict(vc_ece_bundle.get('display_max') or {}),
        'vc_ece_min_display': dict(vc_ece_bundle.get('display_min') or {}),
        'vc_sae_max_display': dict(vc_sae_bundle.get('display_max') or {}),
        'vc_sae_min_display': dict(vc_sae_bundle.get('display_min') or {}),
        'vc_ece_max': dict(vc_ece_bundle.get('display_max') or {}),
        'vc_ece_min': dict(vc_ece_bundle.get('display_min') or {}),
        'vc_sae_max': dict(vc_sae_bundle.get('display_max') or {}),
        'vc_sae_min': dict(vc_sae_bundle.get('display_min') or {}),
        'vc_ece_clip3_detail': vc_ece_clip_detail,
        'vc_sae_clip3_detail': vc_sae_clip_detail,
        'vc_ece_clip3': vc_ece_clip_detail.get('value'),
        'vc_sae_clip3': vc_sae_clip_detail.get('value'),
        'vc_result_modes': {'sae': vc_sae_bundle.get('display_mode'), 'ece': vc_ece_bundle.get('display_mode')},
        'vc_sign_info': {
            'ece_regulatory': sign_ece,
            'ece_display': vc_ece_bundle.get('sign_display'),
            'sae_regulatory': sign_sae,
            'sae_display': vc_sae_bundle.get('sign_display'),
        },
        'compression_sign': {'ece': sign_ece, 'sae': sign_sae},
        'filter_usage': {
            'acc_x': x_meta,
            'acc_y': y_meta,
            'acc_z': z_meta,
            'disp_ece': disp_ece_meta,
            'disp_sae': disp_sae_meta,
        },
        'disp_filter_note': disp_filter_note,
    }


_normalize_force_to_n = normalize_force_to_n


_peak_detail_abs = peak_detail_abs


def compute_femur_metrics(time_s, left_force_n, right_force_n, criterion_key='H3_50%M', left_unit=None, right_unit=None):
    time_arr = np.asarray(time_s, dtype=float)
    left, left_unit_resolved = _normalize_force_to_n(left_force_n, left_unit)
    right, right_unit_resolved = _normalize_force_to_n(right_force_n, right_unit)
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)

    criteria = get_femur_dummy_profile(str(criterion_key))
    limit_n = criteria.get('femur_force_limit_n')

    def _peak_signed(arr, mode='max'):
        arr = np.asarray(arr, dtype=float)
        valid = np.isfinite(time_arr) & np.isfinite(arr)
        if not np.any(valid):
            return {'value': None, 'time_s': None, 'index': None}
        idx = np.flatnonzero(valid)
        valid_values = arr[idx]
        pick = int(np.nanargmax(valid_values) if mode == 'max' else np.nanargmin(valid_values))
        peak_index = int(idx[pick])
        return {'value': float(valid_values[pick]), 'time_s': float(time_arr[peak_index]), 'index': peak_index}

    left_peak_abs = _peak_detail_abs(time_arr, left)
    right_peak_abs = _peak_detail_abs(time_arr, right)
    left_abs = left_peak_abs.get('value')
    right_abs = right_peak_abs.get('value')
    if left_abs is None and right_abs is None:
        overall_peak = {'value': None, 'time_s': None, 'index': None}
        governing_side = None
    elif right_abs is None or (left_abs is not None and left_abs >= right_abs):
        overall_peak = dict(left_peak_abs)
        governing_side = 'LEFT'
    else:
        overall_peak = dict(right_peak_abs)
        governing_side = 'RIGHT'

    passes_limit = True
    if limit_n is not None and overall_peak.get('value') is not None:
        passes_limit = float(overall_peak['value']) <= float(limit_n) + 1e-12

    return {
        'time': time_arr,
        'left_force_n': left,
        'right_force_n': right,
        'left_unit': left_unit_resolved or 'N',
        'right_unit': right_unit_resolved or 'N',
        'left_peak_tension': _peak_signed(left, 'max'),
        'left_peak_compression_raw': _peak_signed(left, 'min'),
        'right_peak_tension': _peak_signed(right, 'max'),
        'right_peak_compression_raw': _peak_signed(right, 'min'),
        'left_peak_abs': left_peak_abs,
        'right_peak_abs': right_peak_abs,
        'overall_peak': overall_peak,
        'governing_side': governing_side,
        'passes_limit': bool(passes_limit),
        'criteria': criteria,
    }
