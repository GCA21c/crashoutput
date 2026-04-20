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
from app.services.injury.chest_metrics import compute_chest_metrics
from app.services.injury.chest_units import (
    convert_accel_to_g_series,
    convert_disp_to_mm_series,
    pick_compression_positive,
)
from app.services.injury.forces import normalize_force_to_n, peak_detail_abs
from app.services.injury.femur_metrics import compute_femur_metrics
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
from app.services.injury.neck_metrics import compute_neck_nij_metrics
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





_convert_accel_to_g_series = convert_accel_to_g_series


_convert_disp_to_mm_series = convert_disp_to_mm_series


_pick_compression_positive = pick_compression_positive
