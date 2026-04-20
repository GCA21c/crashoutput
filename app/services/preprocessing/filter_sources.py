from functools import lru_cache

import numpy as np
import pandas as pd

from app.services.preprocessing.timing import get_time_numeric


@lru_cache(maxsize=64)
def parse_cfc_filter_label(filter_label):
    if filter_label is None:
        return None
    try:
        text = str(filter_label).upper().replace("CFC", "").strip()
        return int(text) if text else None
    except Exception:
        return None


def safe_columns_to_set(columns_like):
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


def resolve_root_source_channel(channel_name, derived_channels=None, original_columns=None):
    derived_channels = dict(derived_channels or {})
    original_columns = safe_columns_to_set(original_columns)
    current = str(channel_name or "")
    seen = set()
    while current and current not in seen:
        if current in original_columns:
            return current
        seen.add(current)
        meta = dict(derived_channels.get(current) or {})
        next_source = str(
            meta.get("root_source_channel")
            or meta.get("raw_source_channel")
            or meta.get("source_channel")
            or ""
        ).strip()
        if not next_source or next_source == current:
            break
        current = next_source
    return current or channel_name


def extract_aligned_original_numeric_series(
    current_df,
    current_time_column,
    original_df,
    original_time_column,
    source_channel,
):
    if current_df is None or current_time_column is None or original_df is None or source_channel not in original_df.columns:
        return None
    if original_time_column is None or original_time_column not in original_df.columns:
        return None

    current_time = get_time_numeric(current_df, current_time_column)
    source_time = get_time_numeric(original_df, original_time_column)
    source_values = pd.to_numeric(original_df[source_channel], errors="coerce").to_numpy(dtype=float)

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


def resolve_effective_time_column(df, preferred_time_column=None):
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


def resolve_filter_source_series(
    current_df,
    current_time_column,
    channel_name,
    original_df=None,
    original_time_column=None,
    derived_channels=None,
):
    effective_current_time_column = resolve_effective_time_column(current_df, current_time_column)
    effective_original_time_column = resolve_effective_time_column(original_df, original_time_column or current_time_column)
    original_columns = getattr(original_df, "columns", []) if original_df is not None else []
    root_source_channel = resolve_root_source_channel(
        channel_name,
        derived_channels=derived_channels,
        original_columns=original_columns,
    )
    aligned = extract_aligned_original_numeric_series(
        current_df,
        effective_current_time_column,
        original_df,
        effective_original_time_column,
        root_source_channel,
    )
    if aligned is not None and np.any(np.isfinite(aligned)):
        return {
            "values": np.asarray(aligned, dtype=float),
            "root_source_channel": root_source_channel,
            "created_from_raw": True,
            "source_mode": "original_raw_aligned",
        }
    fallback = pd.to_numeric(current_df[channel_name], errors="coerce").to_numpy(dtype=float)
    return {
        "values": np.asarray(fallback, dtype=float),
        "root_source_channel": root_source_channel,
        "created_from_raw": False,
        "source_mode": "current_channel_fallback",
    }
