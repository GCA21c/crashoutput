import re
from functools import lru_cache
import numpy as np
import pandas as pd
from scipy.signal import filtfilt

from app.core.dummy import (
    NECK_DUMMY_PROFILES,
    CHEST_DUMMY_PROFILES,
    FEMUR_DUMMY_PROFILES,
    get_neck_dummy_profile,
    get_chest_dummy_profile,
    get_femur_dummy_profile,
)
from app.services.injury.common_engines import compute_3ms_bundle, compute_vc_engine_bundle

FILTER_OPTIONS = ("Raw", "CFC 60", "CFC 180", "CFC 600", "CFC 1000")
OFFSET_SAMPLE_OPTIONS = (100, 300, 1000, 2000)


CHEST_CRITERIA_PRESETS = CHEST_DUMMY_PROFILES
NECK_CRITERIA_PRESETS = NECK_DUMMY_PROFILES
FEMUR_CRITERIA_PRESETS = FEMUR_DUMMY_PROFILES

# Crash CFC filtering is implemented in the SAE J211 phaseless 4-pole
# low-pass direction, with class-specific cutoff handling and stable
# edge treatment for post-processing use.
def get_numeric_channels(df, time_column=None):
    channels = []
    for col in df.columns:
        if time_column is not None and col == time_column:
            continue
        arr = pd.to_numeric(df[col], errors="coerce").to_numpy()
        if np.isfinite(arr).any():
            channels.append(col)
    return channels


def get_time_numeric(df, time_column):
    return pd.to_numeric(df[time_column], errors="coerce").to_numpy()


def find_time0_row(df, time_column):
    time_arr = get_time_numeric(df, time_column)
    valid_rows = np.flatnonzero(np.isfinite(time_arr))
    if valid_rows.size == 0:
        return None
    times = time_arr[valid_rows]
    exact = np.flatnonzero(np.isclose(times, 0.0, atol=1e-12))
    if exact.size:
        return int(valid_rows[exact[0]])
    # Prefer the first non-negative sample when time never hits exact zero,
    # which is usually how trigger alignment is interpreted in crash tools.
    nonneg = np.flatnonzero(times >= 0.0)
    if nonneg.size:
        return int(valid_rows[nonneg[0]])
    nearest = int(np.argmin(np.abs(times)))
    return int(valid_rows[nearest])


def trim_dataframe(df, time_column, start_time, end_time):
    """Trim rows by time while keeping the existing time values untouched.

    Behavior:
    - Remove only rows outside the requested numeric time range.
    - Preserve the original Time values exactly as stored in the dataframe.
    - Do not re-zero, rescale, or regenerate the Time column.
    - Keep non-numeric metadata/header rows.

    This stays intentionally simple so trimming does not introduce any hidden
    time-unit side effects.
    """
    start_time = float(start_time)
    end_time = float(end_time)
    if end_time < start_time:
        start_time, end_time = end_time, start_time
    time_arr = get_time_numeric(df, time_column)
    numeric_mask = np.isfinite(time_arr)
    within_range = numeric_mask & (time_arr >= start_time) & (time_arr <= end_time)
    keep_mask = (~numeric_mask) | within_range
    return df.loc[keep_mask].reset_index(drop=True).copy()


def _get_sample_rate(time_arr):
    x_valid = np.asarray(time_arr, dtype=float)
    x_valid = x_valid[np.isfinite(x_valid)]
    if x_valid.size < 3:
        return None
    diffs = np.diff(x_valid)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if diffs.size == 0:
        return None
    dt = float(np.median(diffs))
    if dt <= 0:
        return None
    return 1.0 / dt


_CFC_SF = {
    60: 2.0775,
    180: 2.0775,
    600: 2.0775,
    1000: 2.0775,
}


def _cfc_coefficients_sae_j211(fs, cfc_value):
    if fs is None or fs <= 0:
        return None
    sf = _CFC_SF.get(int(cfc_value), 2.0775)
    T = 1.0 / float(fs)
    wd = 2.0 * np.pi * float(cfc_value) * float(sf)
    wa = np.tan(wd * T / 2.0)
    den = 1.0 + np.sqrt(2.0) * wa + wa * wa
    if not np.isfinite(den) or den == 0.0:
        return None
    a0 = (wa * wa) / den
    a1 = 2.0 * a0
    a2 = a0
    b1 = -2.0 * ((wa * wa) - 1.0) / den
    b2 = (-1.0 + np.sqrt(2.0) * wa - wa * wa) / den
    # scipy.signal.filtfilt expects direct-form denominator [1, a1, a2] for
    # y[n] = b0*x[n] + ... - a1*y[n-1] - a2*y[n-2]. The SAE/J211 notation in
    # public examples is commonly rearranged as [1, -b1, -b2].
    b = np.asarray([a0, a1, a2], dtype=float)
    a = np.asarray([1.0, -b1, -b2], dtype=float)
    return b, a


def _diadem_zero_magnitude_extend(y_segment, fs):
    """Extend a signal with zero-magnitude mirrored end padding.

    The extension copies a short portion of the original signal at each end,
    applies a zero-centered sign-inverted mirror, and later discards the added
    regions after filtering. In amplitude terms this is a sign-inverted
    reversed copy of the edge data.
    """
    y = np.asarray(y_segment, dtype=float)
    if fs is None or fs <= 0 or y.size < 3:
        return y, 0

    ext_pts = max(1, int(np.ceil(0.010 * float(fs))))
    ext_pts = min(ext_pts, y.size - 1)
    if ext_pts <= 0:
        return y, 0

    pre = -y[:ext_pts][::-1]
    post = -y[-ext_pts:][::-1]
    extended = np.concatenate([pre, y, post])
    return extended, ext_pts



def _apply_cfc_filter_segment(y_segment, fs, cfc_value):
    if fs is None or fs <= 0 or len(y_segment) < 8:
        return y_segment.copy()
    coeffs = _cfc_coefficients_sae_j211(fs, cfc_value)
    if coeffs is None:
        return y_segment.copy()
    b, a = coeffs
    extended, ext_pts = _diadem_zero_magnitude_extend(y_segment, fs)
    try:
        filtered = filtfilt(b, a, extended, method="pad", padtype=None, padlen=0)
        if ext_pts > 0:
            return filtered[ext_pts:ext_pts + len(y_segment)]
        return filtered[:len(y_segment)]
    except Exception:
        return y_segment.copy()


def _replace_with_numeric_series(out, channel_name, values):
    """Preserve original CSV structure and metadata rows.

    Some crash CSV files keep channel description / unit information as ordinary
    rows near the top of the dataframe. Replacing the full column with a pure
    float dtype destroys those rows and later causes channel names such as
    ``Unnamed: 1`` to appear instead of the original descriptions.

    To avoid that, keep the original column as an object series and only
    overwrite rows where the new numeric values are finite.
    """
    original = out[channel_name].copy()
    result = original.astype(object)
    numeric_values = np.asarray(values, dtype=float)
    finite_mask = np.isfinite(numeric_values)
    if finite_mask.any():
        result.iloc[np.flatnonzero(finite_mask)] = numeric_values[finite_mask].tolist()
    out[channel_name] = result


@lru_cache(maxsize=64)
def parse_cfc_filter_label(filter_label):
    if filter_label is None:
        return None
    try:
        text = str(filter_label).upper().replace("CFC", "").strip()
        return int(text) if text else None
    except Exception:
        return None


def _safe_text(*parts):
    return " ".join(str(p or "") for p in parts).lower()


def detect_head_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if "head" not in text or ("acc" not in text and "acceler" not in text):
        return None
    if any(tag in text for tag in (" x ", " ax", "ax ", "acc x", "accx", " acx", "_x", "xa")):
        return "x"
    if any(tag in text for tag in (" y ", " ay", "ay ", "acc y", "accy", " acy", "_y", "ya")):
        return "y"
    if any(tag in text for tag in (" z ", " az", "az ", "acc z", "accz", " acz", "_z", "za")):
        return "z"
    return None


def detect_chest_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if not any(tag in text for tag in ("chest", "chst", "thor", "stern", "rib")):
        return None
    if any(tag in text for tag in ("disp", "defl", "deflection", " ds", "dsx", "dc0", "distance")):
        return "disp"
    if "acc" in text or "acceler" in text:
        if any(tag in text for tag in (" x ", " ax", "ax ", "acc x", "accx", " acx", "_x", "xa")):
            return "x"
        if any(tag in text for tag in (" y ", " ay", "ay ", "acc y", "accy", " acy", "_y", "ya")):
            return "y"
        if any(tag in text for tag in (" z ", " az", "az ", "acc z", "accz", " acz", "_z", "za")):
            return "z"
    return None


def detect_femur_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if not any(tag in text for tag in ("femur", "femr", "thigh", "upper leg", "leg load", "axial force")):
        return None
    if any(tag in text for tag in (" left ", "_l", " lf", "l fem", "lfem", "feml", "driver")):
        return "left"
    if any(tag in text for tag in (" right ", "_r", " rf", "r fem", "rfem", "femr", "passenger")):
        return "right"
    return None


def derived_role_required_cfc(purpose, role):
    purpose = str(purpose or "")
    role = str(role or "")
    if purpose == "neck_injury":
        return neck_role_required_cfc(role)
    if purpose == "head_injury":
        # HEAD X/Y/Z용 별도 CFC1000 파생 채널은 더 이상 생성하지 않는다.
        # DATA FILTERING에서 지정한 필터 등급을 원본 채널 메타데이터로 추적한다.
        return tuple()
    if purpose == "chest_injury":
        # CHEST displacement는 전처리 이력 추적을 위해 SAE J1727용 CFC600 보조 채널을 유지한다.
        # 단, 반드시 원본(raw-aligned) displacement에서 직접 재필터링한 경로만 생성해야 하며,
        # 이미 CFC180 등으로 전처리된 선택 채널을 다시 CFC600으로 거는 이중 필터링은 허용하지 않는다.
        if role == "disp":
            return (600,)
        return tuple()
    if purpose == "femur_injury":
        return tuple()
    return tuple()


def detect_injury_channel_purpose_and_role(channel_name, description="", unit=""):
    role = detect_neck_channel_role(channel_name, description, unit)
    if role is not None:
        return "neck_injury", role
    role = detect_head_channel_role(channel_name, description, unit)
    if role is not None:
        return "head_injury", role
    role = detect_chest_channel_role(channel_name, description, unit)
    if role is not None:
        return "chest_injury", role
    role = detect_femur_channel_role(channel_name, description, unit)
    if role is not None:
        return "femur_injury", role
    return None, None


def make_derived_channel_name(source_channel, purpose, role, cfc_value):
    purpose_tag = str(purpose or "derived").replace("_injury", "").upper()
    return f"{source_channel}__{purpose_tag}_{str(role).upper()}_CFC{int(cfc_value)}"


def detect_neck_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if "neck" not in text:
        return None
    if any(tag in text for tag in (" mocy", "occipital condyle", " moment y", " my ", "_my", "my_", "flex", "ext")):
        return "my"
    if any(tag in text for tag in (" force z", " fz ", "_fz", "fz_", "axial")):
        return "fz"
    if any(tag in text for tag in (" force x", " fx ", "_fx", "fx_", "shear")):
        return "fx"
    return None


def neck_role_required_cfc(role):
    """Return only the *additional* Neck CFC channels that may be needed later.

    The main DATA FILTERING step already applies the user-selected CFC directly to the
    original Neck channels. For the current workflow, users typically preprocess:
      - Fx/Fy/Fz -> CFC1000
      - Mx/My/Mz -> CFC600

    So we should not create duplicate derivative channels with the same effective CFC,
    such as Fx-CFC1000, Fz-CFC1000, or My-CFC600. The only commonly needed extra
    paths for Neck injury calculation are the alternate CFC600 force channels.
    """
    if role in ("fz", "fx"):
        return (600,)
    if role == "my":
        return tuple()
    return tuple()


def make_neck_derived_channel_name(source_channel, role, cfc_value):
    return f"{source_channel}__NECK_{str(role).upper()}_CFC{int(cfc_value)}"


def _safe_columns_to_set(columns_like):
    if columns_like is None:
        return set()
    try:
        if isinstance(columns_like, pd.Index):
            return set(columns_like.tolist())
    except Exception:
        pass
    if isinstance(columns_like, (list, tuple, set)):
        return set(columns_like)
    try:
        return set(list(columns_like))
    except Exception:
        return {columns_like} if columns_like else set()


def _resolve_root_source_channel(channel_name, derived_channels=None, original_columns=None):
    derived_channels = dict(derived_channels or {})
    original_columns = _safe_columns_to_set(original_columns)
    current = str(channel_name or '')
    seen = set()
    while current and current not in seen:
        if current in original_columns:
            return current
        seen.add(current)
        meta = dict(derived_channels.get(current) or {})
        next_source = str(meta.get('root_source_channel') or meta.get('raw_source_channel') or meta.get('source_channel') or '').strip()
        if not next_source or next_source == current:
            break
        current = next_source
    return current or channel_name



def _extract_aligned_original_numeric_series(current_df, current_time_column, original_df, original_time_column, source_channel):
    if current_df is None or current_time_column is None or original_df is None or source_channel not in original_df.columns:
        return None
    if original_time_column is None or original_time_column not in original_df.columns:
        return None

    current_time = get_time_numeric(current_df, current_time_column)
    source_time = get_time_numeric(original_df, original_time_column)
    source_values = pd.to_numeric(original_df[source_channel], errors='coerce').to_numpy(dtype=float)

    out = np.full(len(current_df), np.nan, dtype=float)
    valid_source = np.isfinite(source_time) & np.isfinite(source_values)
    valid_current = np.isfinite(current_time)
    if np.count_nonzero(valid_source) < 2 or not np.any(valid_current):
        return out

    xs = source_time[valid_source]
    ys = source_values[valid_source]
    order = np.argsort(xs)
    xs = xs[order]
    ys = ys[order]
    uniq, uniq_idx = np.unique(xs, return_index=True)
    xs = uniq
    ys = ys[uniq_idx]
    if xs.size < 2:
        return out

    target = current_time[valid_current]
    inside = (target >= xs[0]) & (target <= xs[-1])
    if np.any(inside):
        interp = np.interp(target[inside], xs, ys)
        idx = np.flatnonzero(valid_current)
        out[idx[inside]] = interp
    return out



def _resolve_effective_time_column(df, preferred_time_column=None):
    if df is None or getattr(df, "columns", None) is None:
        return None
    if preferred_time_column and preferred_time_column in df.columns:
        return preferred_time_column
    for candidate in ("Time", "time", "TIME"):
        if candidate in df.columns:
            return candidate
    for col in df.columns:
        text = str(col).strip().lower()
        if text == "time" or text.startswith("time(") or text.startswith("time ["):
            return col
    return None


def _resolve_filter_source_series(current_df, current_time_column, channel_name, original_df=None, original_time_column=None, derived_channels=None):
    effective_current_time_column = _resolve_effective_time_column(current_df, current_time_column)
    effective_original_time_column = _resolve_effective_time_column(original_df, original_time_column or current_time_column)
    original_columns = getattr(original_df, 'columns', []) if original_df is not None else []
    root_source_channel = _resolve_root_source_channel(channel_name, derived_channels=derived_channels, original_columns=original_columns)
    aligned = _extract_aligned_original_numeric_series(
        current_df,
        effective_current_time_column,
        original_df,
        effective_original_time_column,
        root_source_channel,
    )
    if aligned is not None and np.any(np.isfinite(aligned)):
        return {
            'values': np.asarray(aligned, dtype=float),
            'root_source_channel': root_source_channel,
            'created_from_raw': True,
            'source_mode': 'original_raw_aligned',
        }
    fallback = pd.to_numeric(current_df[channel_name], errors='coerce').to_numpy(dtype=float)
    return {
        'values': np.asarray(fallback, dtype=float),
        'root_source_channel': root_source_channel,
        'created_from_raw': False,
        'source_mode': 'current_channel_fallback',
    }


def apply_filtering_with_derivatives(
    df,
    time_column,
    channel_to_filter,
    descriptions=None,
    units=None,
    existing_filter_labels=None,
    existing_derived_channels=None,
    original_df=None,
    original_time_column=None,
):
    out = apply_filtering(df, time_column, channel_to_filter)
    descriptions = dict(descriptions or {})
    units = dict(units or {})
    filter_labels = dict(existing_filter_labels or {})
    derived_channels = dict(existing_derived_channels or {})

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

    for channel_name in channel_to_filter.keys():
        purpose, role = detect_injury_channel_purpose_and_role(
            channel_name,
            descriptions.get(channel_name, ""),
            units.get(channel_name, ""),
        )
        if purpose is None or role is None:
            continue

        raw_y = pd.to_numeric(df[channel_name], errors="coerce").to_numpy(dtype=float)
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
                "role": role,
                "filter_label": f"CFC {int(cfc_value)}",
                "display_filter_label": f"CFC {int(cfc_value)}",
                "required_cfc": f"CFC {int(cfc_value)}",
                "cfc_value": int(cfc_value),
                "purpose": purpose,
            }
            if purpose == "chest_injury" and role == "disp":
                derived_meta["created_from_raw"] = True
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


def get_offset_sample_rows(df, time_column, sample_count, time0_row=None, include_time0=True):
    """Return offset rows from data start toward Time0.

    New baseline rule:
    - build the candidate region from the first valid numeric time sample
      through Time0
    - then take up to ``sample_count`` rows from the *start* of that region

    This replaces the old "last n samples before Time0" behavior.
    """
    time_arr = get_time_numeric(df, time_column)
    numeric_rows = np.flatnonzero(np.isfinite(time_arr))
    if numeric_rows.size == 0:
        return np.asarray([], dtype=int)

    if time0_row is None:
        time0_row = find_time0_row(df, time_column)
    if time0_row is None:
        return np.asarray([], dtype=int)

    side = "right" if include_time0 else "left"
    end_pos = int(np.searchsorted(numeric_rows, time0_row, side=side))
    if end_pos <= 0:
        return np.asarray([], dtype=int)

    sample_count = max(0, int(sample_count))
    if sample_count <= 0:
        return np.asarray([], dtype=int)

    return numeric_rows[:min(end_pos, sample_count)]



def apply_offset(df, time_column, channel_names, sample_count, time0_row=None):
    """Apply baseline offset to every requested numeric channel.

    The preview/reference channel in the UI is only for visualization. This
    function subtracts each channel's own mean offset from that channel across
    the whole valid numeric region, excluding only the Time column.

    Offset mean basis:
    - start at the first valid numeric sample in the dataset
    - include rows up to Time0
    - use up to the first ``sample_count`` rows in that start-to-Time0 region
    """
    out = df.copy(deep=True)
    sample_rows = get_offset_sample_rows(out, time_column, sample_count, time0_row=time0_row, include_time0=True)
    if sample_rows.size == 0:
        return out, {}

    offsets = {}
    for channel_name in channel_names:
        y = pd.to_numeric(out[channel_name], errors="coerce").to_numpy(dtype=float)
        valid_sample_rows = sample_rows[np.isfinite(y[sample_rows])]
        if valid_sample_rows.size == 0:
            continue
        mean_value = float(np.mean(y[valid_sample_rows]))
        if not np.isfinite(mean_value):
            continue
        offsets[channel_name] = mean_value
        corrected = y.copy()
        finite_rows = np.flatnonzero(np.isfinite(corrected))
        corrected[finite_rows] = corrected[finite_rows] - mean_value
        _replace_with_numeric_series(out, channel_name, corrected)

    return out, offsets


def make_channel_search_text(viewer, channel_name):
    label = viewer.get_channel_display_name(channel_name)
    return f"{channel_name} {label}".lower()


def infer_channel_group_key(viewer, channel_name):
    label = viewer.get_channel_display_name(channel_name).strip() or str(channel_name)
    text = f"{channel_name} {label}"
    text = re.sub(r"\[[^\]]*\]", " ", text)
    tokens = re.findall(r"[A-Za-z]+", text.upper())
    if not tokens:
        return "ETC"
    filtered = [tok for tok in tokens if tok not in {"X", "Y", "Z", "LEFT", "RIGHT", "RAW", "TIME", "SEC", "MS"}]
    if filtered:
        return filtered[0]
    return tokens[0]



def _series_to_float(arr):
    values = np.asarray(arr, dtype=float)
    return values[np.isfinite(values)]


def _convert_accel_to_g(values, unit_text=""):
    unit = str(unit_text or "").lower().replace(" ", "")
    vals = np.asarray(values, dtype=float)
    if "m/s" in unit or "ms-2" in unit or "mps2" in unit:
        return vals / 9.80665
    return vals


def _find_resultant_or_axis(viewer, keywords):
    candidates = []
    for col in viewer.get_numeric_channel_names(exclude_time=True):
        name = str(col).lower()
        label = str(viewer.get_channel_display_name(col)).lower()
        unit = str(viewer.get_y_axis_label(col)).lower()
        text = f"{name} {label} {unit}"
        score = 0
        for kw in keywords:
            if kw in text:
                score += 3
        if "res" in text or "resultant" in text or "mag" in text:
            score += 2
        if score > 0:
            candidates.append((score, col))
    candidates.sort(key=lambda x: (-x[0], str(x[1])))
    return candidates[0][1] if candidates else None


def auto_detect_injury_channels(viewer):
    found = {}
    head = _find_resultant_or_axis(viewer, ["head", "cg", "acc"])
    if head:
        found["Head Acceleration"] = head

    # neck force / moment heuristics
    for col in viewer.get_numeric_channel_names(exclude_time=True):
        text = f"{col} {viewer.get_channel_display_name(col)} {viewer.get_y_axis_label(col)}".lower()
        if "neck" in text and ("fx" in text or "force x" in text or "axial" in text):
            found.setdefault("Neck Fx", col)
        if "neck" in text and ("my" in text or "moment y" in text or "flex" in text or "ext" in text):
            found.setdefault("Neck My", col)
    return found


def _cumtrapz(y, x):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(y, dtype=float)
    if y.size <= 1:
        return out
    out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return out


def _prepare_hic_series(time_s, accel_g):
    t = np.asarray(time_s, dtype=float)
    a = np.asarray(accel_g, dtype=float)
    valid = np.isfinite(t) & np.isfinite(a)
    t = t[valid]
    a = a[valid]
    if t.size < 3:
        return None, None

    order = np.argsort(t, kind='mergesort')
    t = t[order]
    a = a[order]

    keep = np.ones(t.size, dtype=bool)
    keep[1:] = np.diff(t) > 0.0
    t = t[keep]
    a = a[keep]
    if t.size < 3:
        return None, None
    return t, a



def _integral_at_query(query_t, t, a, integ):
    q = float(query_t)
    if q <= float(t[0]):
        return 0.0
    if q >= float(t[-1]):
        return float(integ[-1])

    idx = int(np.searchsorted(t, q, side='right') - 1)
    if idx < 0:
        return 0.0
    if idx >= len(t) - 1:
        return float(integ[-1])

    t0 = float(t[idx])
    t1 = float(t[idx + 1])
    a0 = float(a[idx])
    a1 = float(a[idx + 1])
    dt = t1 - t0
    if dt <= 0.0:
        return float(integ[idx])

    dq = q - t0
    slope = (a1 - a0) / dt
    aq = a0 + slope * dq
    partial = 0.5 * (a0 + aq) * dq
    return float(integ[idx] + partial)



def _value_at_query(query_t, t, a):
    q = float(query_t)
    if q <= float(t[0]):
        return float(a[0])
    if q >= float(t[-1]):
        return float(a[-1])
    return float(np.interp(q, t, a))



def _update_best_hic(best_info, start_time, end_time, area, full_time, full_signal):
    dt = float(end_time - start_time)
    if dt <= 0.0:
        return best_info
    mean_a = float(area / dt)
    hic = float(dt * (abs(mean_a) ** 2.5))
    if (best_info is None) or (hic > best_info['value'] + 1e-15):
        return {
            'value': hic,
            'start_time': float(start_time),
            'end_time': float(end_time),
            'duration': dt,
            'mean_accel_g': mean_a,
            'time': full_time.copy(),
            'signal': full_signal.copy(),
        }
    return best_info



def compute_hic_details(time_s, accel_g, max_window_s=0.036):
    t, a = _prepare_hic_series(time_s, accel_g)
    if t is None:
        return None

    integ = _cumtrapz(a, t)
    n = t.size
    window = float(max_window_s)
    best_info = None

    # 1) Exact sample-to-sample candidates using the real time channel.
    j = 1
    for i in range(n - 1):
        if j < i + 1:
            j = i + 1
        while j < n and (t[j] - t[i]) <= window + 1e-15:
            j += 1
        end_limit = j - 1
        for k in range(i + 1, end_limit + 1):
            area = float(integ[k] - integ[i])
            best_info = _update_best_hic(best_info, t[i], t[k], area, t, a)

    # 2) Exact full-window end candidates at t[i] + window using linear interpolation.
    for i in range(n - 1):
        end_t = float(t[i] + window)
        if end_t > float(t[-1]) + 1e-15:
            break
        area = _integral_at_query(end_t, t, a, integ) - float(integ[i])
        best_info = _update_best_hic(best_info, t[i], end_t, area, t, a)

    # 3) Exact full-window start candidates at t[j] - window using linear interpolation.
    for j in range(1, n):
        start_t = float(t[j] - window)
        if start_t < float(t[0]) - 1e-15:
            continue
        area = float(integ[j]) - _integral_at_query(start_t, t, a, integ)
        best_info = _update_best_hic(best_info, start_t, t[j], area, t, a)

    if best_info is None:
        return None

    # Keep the plotted signal aligned with the selected interval representation.
    start_y = _value_at_query(best_info['start_time'], t, a)
    end_y = _value_at_query(best_info['end_time'], t, a)
    best_info['interval_signal'] = {
        'start_value': start_y,
        'end_value': end_y,
    }
    return best_info




def _level_exceedance_intervals(time_s, signal, level):
    t, y = _prepare_hic_series(time_s, signal)
    if t is None:
        return [], None, None
    lvl = float(level)
    intervals = []
    in_interval = bool(y[0] > lvl)
    start_t = float(t[0]) if in_interval else None
    for i in range(len(t) - 1):
        t0 = float(t[i])
        t1 = float(t[i + 1])
        y0 = float(y[i])
        y1 = float(y[i + 1])
        above0 = y0 > lvl
        above1 = y1 > lvl
        if above0 == above1:
            continue
        if np.isclose(y1, y0, rtol=0.0, atol=1e-15):
            cross_t = t1
        else:
            cross_t = t0 + (lvl - y0) * (t1 - t0) / (y1 - y0)
        cross_t = float(min(max(cross_t, t0), t1))
        if above0 and not above1:
            if in_interval and start_t is not None:
                intervals.append((float(start_t), cross_t))
            in_interval = False
            start_t = None
        elif (not above0) and above1:
            start_t = cross_t
            in_interval = True
    if in_interval and start_t is not None:
        intervals.append((float(start_t), float(t[-1])))
    return intervals, t, y


def _clip_exceedance_detail(time_s, signal, window_s=0.003, mode='single', use_abs=True):
    arr = np.asarray(signal, dtype=float)
    arr_eval = np.abs(arr) if use_abs else arr
    intervals0, t, y = _level_exceedance_intervals(time_s, arr_eval, 0.0)
    if t is None or y is None or t.size < 2:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }
    total_span = float(t[-1] - t[0])
    if total_span <= 0.0:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }

    req = float(window_s)

    def predicate(level):
        intervals, _, _ = _level_exceedance_intervals(t, y, level)
        if not intervals:
            return False, intervals
        if mode == 'single':
            ok = any((b - a) >= req - 1e-15 for a, b in intervals)
        else:
            ok = sum((b - a) for a, b in intervals) >= req - 1e-15
        return ok, intervals

    lo = 0.0
    hi = float(np.nanmax(y[np.isfinite(y)])) if np.isfinite(y).any() else 0.0
    best_intervals = []
    ok0, ints0 = predicate(lo)
    if not ok0:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }
    best_intervals = ints0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        ok, intervals = predicate(mid)
        if ok:
            lo = mid
            best_intervals = intervals
        else:
            hi = mid
    value = float(lo)
    intervals, _, _ = _level_exceedance_intervals(t, y, value)
    if not intervals:
        intervals = best_intervals
    if not intervals:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }

    if mode == 'single':
        start_t, end_t = max(intervals, key=lambda ab: (ab[1] - ab[0], -ab[0]))
        duration_s = float(end_t - start_t)
    else:
        start_t = float(intervals[0][0])
        end_t = float(intervals[-1][1])
        duration_s = float(sum((b - a) for a, b in intervals))
    center_t = 0.5 * (start_t + end_t)
    idx = int(np.argmin(np.abs(t - center_t)))
    return {
        'value': value,
        'time_s': center_t,
        'index': idx,
        'start_time_s': start_t,
        'end_time_s': end_t,
        'duration_s': duration_s,
        'start_value': _value_at_query(start_t, t, y),
        'end_value': _value_at_query(end_t, t, y),
        'mean_value': None,
        'method': f'3ms_exceedance_{mode}',
    }


def compute_3ms_one_peak_exceedance_details(time_s, signal, use_abs=True, window_s=0.003):
    return _clip_exceedance_detail(time_s, signal, window_s=window_s, mode='single', use_abs=use_abs)


def _estimate_constant_dt(time_s):
    t = np.asarray(time_s, dtype=float)
    t = t[np.isfinite(t)]
    if t.size < 3:
        return None
    diffs = np.diff(t)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if diffs.size == 0:
        return None
    dt = float(np.median(diffs))
    if not np.isfinite(dt) or dt <= 0.0:
        return None
    # Treat the signal as constant-sample-rate only when all positive steps stay
    # close to the median. This follows the Xms simplified cumulative algorithm
    # used in crash-analysis guidance for constant sampling rates.
    tol = max(1e-12, dt * 0.02)
    if np.nanmax(np.abs(diffs - dt)) > tol:
        return None
    return dt


def compute_3ms_multiple_peak_exceedance_details(time_s, signal, use_abs=True, window_s=0.003):
    """Return cumulative Xms details using the constant-rate sorting rule when possible.

    Crash-analysis guidance describes Xms multiple-peak / cumulative calculation for
    constant sample rates as: sort amplitudes in descending order, then take the
    value reached after x ms. For display, reconstruct the corresponding threshold
    crossing intervals on the original time axis. For non-uniform sampling, fall back
    to the continuous threshold-duration approach.
    """
    t, y_src = _prepare_hic_series(time_s, signal)
    empty = {
        'value': None,
        'time_s': None,
        'index': None,
        'start_time_s': None,
        'end_time_s': None,
        'duration_s': None,
        'start_value': None,
        'end_value': None,
        'mean_value': None,
        'method': '3ms_exceedance_multiple',
    }
    if t is None:
        return empty

    y = np.abs(y_src) if use_abs else y_src
    dt = _estimate_constant_dt(t)
    req = float(window_s)
    if dt is None or req <= 0.0:
        return _clip_exceedance_detail(time_s, signal, window_s=window_s, mode='multiple', use_abs=use_abs)

    samples_required = max(1, int(np.ceil((req - 1e-15) / dt)))
    finite_vals = y[np.isfinite(y)]
    if finite_vals.size < samples_required:
        return empty

    sorted_vals = np.sort(finite_vals)[::-1]
    value = float(sorted_vals[samples_required - 1])

    # Reconstruct cumulative threshold-crossing intervals on the original signal.
    # Use a tiny epsilon below the sorted threshold so tied samples at the cut-off
    # remain included in the duration accounting, which more closely matches how
    # sample-based cumulative Xms is reported in crash tools.
    eps = max(1e-12, abs(value) * 1e-12)
    intervals, t2, y2 = _level_exceedance_intervals(t, y, value - eps)
    if not intervals:
        return _clip_exceedance_detail(time_s, signal, window_s=window_s, mode='multiple', use_abs=use_abs)

    start_t = float(intervals[0][0])
    end_t = float(intervals[-1][1])
    duration_s = float(sum((b - a) for a, b in intervals))
    center_t = 0.5 * (start_t + end_t)
    idx = int(np.argmin(np.abs(t2 - center_t))) if t2.size else None
    return {
        'value': value,
        'time_s': center_t,
        'index': idx,
        'start_time_s': start_t,
        'end_time_s': end_t,
        'duration_s': duration_s,
        'start_value': _value_at_query(start_t, t2, y2),
        'end_value': _value_at_query(end_t, t2, y2),
        'mean_value': None,
        'method': '3ms_cumulative_sorted_constant_rate',
    }

def compute_hic(time_s, accel_g, max_window_s=0.036):
    info = compute_hic_details(time_s, accel_g, max_window_s=max_window_s)
    return None if info is None else float(info['value'])


def compute_3ms_clip_details(time_s, signal, use_abs=True, window_s=0.003):
    """
    Exact 3 ms clip implementation using fixed-duration windows.

    Uses the real time channel, exact fixed-duration windows, linear interpolation at
    window boundaries, and trapezoidal integration over the interpolated signal.
    This avoids the common sample-count-only approximation.
    """
    t, y_src = _prepare_hic_series(time_s, signal)
    if t is None:
        return {
            "value": None,
            "time_s": None,
            "index": None,
            "start_time_s": None,
            "end_time_s": None,
            "duration_s": None,
            "start_value": None,
            "end_value": None,
            "mean_value": None,
            "method": "exact_3ms_window",
        }

    y = np.abs(y_src) if use_abs else y_src
    integ = _cumtrapz(y, t)
    window = float(window_s)
    if t.size < 2 or window <= 0.0 or (float(t[-1]) - float(t[0])) < window - 1e-15:
        return {
            "value": None,
            "time_s": None,
            "index": None,
            "start_time_s": None,
            "end_time_s": None,
            "duration_s": None,
            "start_value": None,
            "end_value": None,
            "mean_value": None,
            "method": "exact_3ms_window",
        }

    best = None

    def _consider_window(start_t, end_t):
        nonlocal best
        dt = float(end_t - start_t)
        if dt <= 0.0:
            return
        area = _integral_at_query(end_t, t, y, integ) - _integral_at_query(start_t, t, y, integ)
        mean_v = float(area / dt)
        if (best is None) or (mean_v > best["value"] + 1e-15):
            center_t = 0.5 * (float(start_t) + float(end_t))
            idx = int(np.argmin(np.abs(t - center_t)))
            best = {
                "value": mean_v,
                "time_s": center_t,
                "index": idx,
                "start_time_s": float(start_t),
                "end_time_s": float(end_t),
                "duration_s": dt,
                "start_value": _value_at_query(start_t, t, y),
                "end_value": _value_at_query(end_t, t, y),
                "mean_value": mean_v,
                "method": "exact_3ms_window",
            }

    # Exact full-window candidates anchored at every sample start.
    for i in range(len(t) - 1):
        start_t = float(t[i])
        end_t = start_t + window
        if end_t > float(t[-1]) + 1e-15:
            break
        _consider_window(start_t, end_t)

    # Exact full-window candidates anchored at every sample end.
    for j in range(1, len(t)):
        end_t = float(t[j])
        start_t = end_t - window
        if start_t < float(t[0]) - 1e-15:
            continue
        _consider_window(start_t, end_t)

    if best is None:
        return {
            "value": None,
            "time_s": None,
            "index": None,
            "start_time_s": None,
            "end_time_s": None,
            "duration_s": None,
            "start_value": None,
            "end_value": None,
            "mean_value": None,
            "method": "exact_3ms_window",
        }
    return best


def compute_3ms_clip(time_s, signal):
    return compute_3ms_one_peak_exceedance_details(time_s, signal, use_abs=True).get("value")


def compute_3ms_one_peak_details(time_s, signal, use_abs=True):
    t = np.asarray(time_s, dtype=float)
    y_raw = np.asarray(signal, dtype=float)
    y = np.abs(y_raw) if use_abs else y_raw
    valid = np.isfinite(t) & np.isfinite(y)
    t = t[valid]
    y = y[valid]
    if t.size < 3:
        return {"value": None, "time_s": None, "index": None, "start_time_s": None, "end_time_s": None}

    def _strict_peaks(arr):
        if arr.size < 3:
            return np.array([], dtype=int)
        mid = arr[1:-1]
        return np.flatnonzero((mid > arr[:-2]) & (mid >= arr[2:])) + 1

    def _strict_valleys(arr):
        if arr.size < 3:
            return np.array([], dtype=int)
        mid = arr[1:-1]
        return np.flatnonzero((mid < arr[:-2]) & (mid <= arr[2:])) + 1

    peak_idx = _strict_peaks(y)
    if peak_idx.size == 0:
        return compute_3ms_clip_details(t, y_raw if not use_abs else y, use_abs=False)

    valley_idx = np.unique(np.concatenate(([0], _strict_valleys(y), [len(y) - 1]))).astype(int)
    best = None
    for pk in peak_idx:
        left_candidates = valley_idx[valley_idx < pk]
        right_candidates = valley_idx[valley_idx > pk]
        left = int(left_candidates[-1]) if left_candidates.size else 0
        right = int(right_candidates[0]) if right_candidates.size else (len(y) - 1)
        if right - left + 1 < 3:
            continue
        seg_t = t[left:right + 1]
        seg_y = y[left:right + 1]
        detail = compute_3ms_clip_details(seg_t, seg_y, use_abs=False)
        if detail.get('value') is None:
            continue
        if (best is None) or (float(detail['value']) > float(best['value']) + 1e-15):
            detail = dict(detail)
            if detail.get('index') is not None:
                detail['index'] = int(left + int(detail['index']))
            best = detail
    if best is not None:
        return best
    return compute_3ms_clip_details(t, y_raw if not use_abs else y, use_abs=False)


def compute_nij(fx_n, my_nm):
    nij_series = compute_nij_series(fx_n, my_nm)
    valid = nij_series[np.isfinite(nij_series)]
    return float(np.nanmax(valid)) if valid.size else None


def compute_resultant_xyz(x, y, z):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    return np.sqrt(np.square(x) + np.square(y) + np.square(z))


def compute_nij_series(fx_n, my_nm):
    fx = np.asarray(fx_n, dtype=float)
    my = np.asarray(my_nm, dtype=float)
    valid = np.isfinite(fx) & np.isfinite(my)
    out = np.full_like(fx, np.nan, dtype=float)
    if not np.any(valid):
        return out
    fzc = 6160.0
    fzt = 6806.0
    myf = 310.0
    mye = 125.0
    fxv = fx[valid]
    myv = my[valid]
    f_term = np.where(fxv >= 0, fxv / fzt, (-fxv) / fzc)
    m_term = np.where(myv >= 0, myv / myf, (-myv) / mye)
    out[valid] = f_term + m_term
    return out


def compute_injury_metrics(viewer, detected_channels):
    results = []
    if viewer.df is None or viewer.time_column is None:
        return results
    time_s = viewer.get_numeric_column(viewer.time_column)

    head_ch = detected_channels.get("Head Acceleration")
    if head_ch:
        unit = viewer.get_y_axis_label(head_ch)
        accel = _convert_accel_to_g(viewer.get_numeric_column(head_ch), unit)
        hic15 = compute_hic(time_s, accel, 0.015)
        hic36 = compute_hic(time_s, accel, 0.036)
        clip3 = compute_3ms_clip(time_s, accel)
        if hic15 is not None:
            results.append({"metric": "HIC15", "value": f"{hic15:.3f}", "unit": "-", "source": head_ch})
        if hic36 is not None:
            results.append({"metric": "HIC36", "value": f"{hic36:.3f}", "unit": "-", "source": head_ch})
        if clip3 is not None:
            results.append({"metric": "Head 3ms Clip", "value": f"{clip3:.3f}", "unit": "g", "source": head_ch})

    fx_ch = detected_channels.get("Neck Fx")
    my_ch = detected_channels.get("Neck My")
    if fx_ch and my_ch:
        nij = compute_nij(viewer.get_numeric_column(fx_ch), viewer.get_numeric_column(my_ch))
        if nij is not None:
            results.append({"metric": "Nij", "value": f"{nij:.3f}", "unit": "-", "source": f"{fx_ch} + {my_ch}"})

    return results



def apply_cfc_filter_to_series(time_arr, values, cfc_value):
    x_all = np.asarray(time_arr, dtype=float)
    y_all = np.asarray(values, dtype=float)
    out = y_all.copy()
    fs = _get_sample_rate(x_all)
    valid = np.isfinite(x_all) & np.isfinite(y_all)
    if not np.any(valid):
        return out
    idx = np.flatnonzero(valid)
    split_points = np.where(np.diff(idx) > 1)[0] + 1
    groups = np.split(idx, split_points)
    for grp in groups:
        if grp.size < 8:
            continue
        out[grp] = _apply_cfc_filter_segment(y_all[grp].astype(float), fs, cfc_value)
    return out




def build_neck_injury_channels(metrics):
    """Build calculated neck injury channels for saving to _I datasets.

    Avoid saving duplicate intermediate channels when the selected/used input already
    has the same effective CFC label.
    """
    if not metrics:
        return {}

    def _same_cfc(label, cfc_value):
        parsed = parse_cfc_filter_label(label)
        return parsed == int(cfc_value)

    used_filters = dict((metrics or {}).get('used_filter_labels') or {})
    out = {}
    if metrics.get('fz_peak_filtered') is not None and not _same_cfc(used_filters.get('fz_peak'), 1000):
        out['NECKUP_FZ_CFC1000'] = np.asarray(metrics['fz_peak_filtered'], dtype=float)
    if metrics.get('fz_nij_filtered') is not None and not _same_cfc(used_filters.get('fz_nij'), 600):
        out['NECKUP_FZ_CFC600'] = np.asarray(metrics['fz_nij_filtered'], dtype=float)
    if metrics.get('fx_filtered') is not None and not _same_cfc(used_filters.get('fx_nij'), 600):
        out['NECKUP_FX_CFC600'] = np.asarray(metrics['fx_filtered'], dtype=float)
    if metrics.get('my_raw_filtered') is not None and not _same_cfc(used_filters.get('my_nij'), 600):
        out['NECKUP_MY_CFC600'] = np.asarray(metrics['my_raw_filtered'], dtype=float)
    if metrics.get('my_filtered') is not None:
        out['NECKUP_MOCY'] = np.asarray(metrics['my_filtered'], dtype=float)
    out['NECKUP_NIJ_TE'] = np.asarray(metrics.get('nte'), dtype=float)
    out['NECKUP_NIJ_TF'] = np.asarray(metrics.get('ntf'), dtype=float)
    out['NECKUP_NIJ_CE'] = np.asarray(metrics.get('nce'), dtype=float)
    out['NECKUP_NIJ_CF'] = np.asarray(metrics.get('ncf'), dtype=float)
    out['NECKUP_NIJ'] = np.asarray(metrics.get('nij'), dtype=float)
    return out


def build_neck_injury_channel_metadata(metrics):
    crit = dict((metrics or {}).get('criteria') or {})
    moment_label = crit.get('input_moment', 'MOCy')
    descriptions = {
        'NECKUP_FZ_CFC1000': 'Upper Neck Fz - CFC1000',
        'NECKUP_FZ_CFC600': 'Upper Neck Fz - CFC600',
        'NECKUP_FX_CFC600': 'Upper Neck Fx - CFC600',
        'NECKUP_MY_CFC600': 'Upper Neck My - CFC600',
        'NECKUP_MOCY': 'Occipital Condyle Moment - Y',
        'NECKUP_NIJ_TE': 'Upper Neck Nij - Tension Extension',
        'NECKUP_NIJ_TF': 'Upper Neck Nij - Tension Flexion',
        'NECKUP_NIJ_CE': 'Upper Neck Nij - Compression Extension',
        'NECKUP_NIJ_CF': 'Upper Neck Nij - Compression Flexion',
        'NECKUP_NIJ': 'Upper Neck Nij',
    }
    units = {
        'NECKUP_FZ_CFC1000': 'N',
        'NECKUP_FZ_CFC600': 'N',
        'NECKUP_FX_CFC600': 'N',
        'NECKUP_MY_CFC600': 'Nm',
        'NECKUP_MOCY': 'Nm',
        'NECKUP_NIJ_TE': 'Value',
        'NECKUP_NIJ_TF': 'Value',
        'NECKUP_NIJ_CE': 'Value',
        'NECKUP_NIJ_CF': 'Value',
        'NECKUP_NIJ': 'Value',
    }
    nij_filter = crit.get('filter', 'CFC 600') or 'CFC 600'
    filter_labels = {
        'NECKUP_FZ_CFC1000': 'CFC 1000',
        'NECKUP_FZ_CFC600': 'CFC 600',
        'NECKUP_FX_CFC600': 'CFC 600',
        'NECKUP_MY_CFC600': 'CFC 600',
        'NECKUP_MOCY': nij_filter,
        'NECKUP_NIJ_TE': nij_filter,
        'NECKUP_NIJ_TF': nij_filter,
        'NECKUP_NIJ_CE': nij_filter,
        'NECKUP_NIJ_CF': nij_filter,
        'NECKUP_NIJ': nij_filter,
    }
    return {'descriptions': descriptions, 'units': units, 'channel_filter_labels': filter_labels}

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



def _convert_accel_to_g_series(values, unit_text=''):
    arr = np.asarray(values, dtype=float)
    unit = str(unit_text or '').lower().replace(' ', '')
    if 'm/s' in unit or 'ms-2' in unit or 'mps2' in unit:
        return arr / 9.80665
    return arr


def _convert_disp_to_mm_series(values, unit_text=''):
    arr = np.asarray(values, dtype=float)
    unit = str(unit_text or '').lower().replace(' ', '')
    if unit in ('m', 'meter', 'meters'):
        return arr * 1000.0
    if unit in ('cm', 'centimeter', 'centimeters'):
        return arr * 10.0
    if unit in ('mm', 'millimeter', 'millimeters', ''):
        return arr
    if unit in ('in', 'inch', 'inches'):
        return arr * 25.4
    return arr


def _pick_compression_positive(values_mm):
    arr = np.asarray(values_mm, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return 1.0
    vmax = np.nanmax(finite)
    vmin = np.nanmin(finite)
    return 1.0 if abs(vmax) >= abs(vmin) else -1.0


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
    peak_3ms_bundle = compute_3ms_bundle(t, res_g, use_abs=True, include_res_peak=True)
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


def _normalize_force_to_n(values, unit_text):
    arr = np.asarray(values, dtype=float)
    unit = str(unit_text or '').strip().lower().replace(' ', '')
    if unit in ('kn', 'kilonewton', 'kilonewtons'):
        return arr * 1000.0, 'N'
    if unit in ('mn',):
        return arr * 1_000_000.0, 'N'
    if unit in ('lbf', 'lb', 'lbs', 'poundforce', 'poundsforce'):
        return arr * 4.4482216152605, 'N'
    return arr, ('N' if not unit else str(unit_text or ''))


def _peak_detail_abs(time_arr, values):
    t = np.asarray(time_arr, dtype=float)
    y = np.asarray(values, dtype=float)
    valid = np.isfinite(t) & np.isfinite(y)
    if not np.any(valid):
        return {'value': None, 'time_s': None, 'index': None}
    idx = np.flatnonzero(valid)
    peak_local = int(np.nanargmax(np.abs(y[idx])))
    peak_index = int(idx[peak_local])
    return {'value': float(abs(y[peak_index])), 'time_s': float(t[peak_index]), 'index': peak_index}


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
