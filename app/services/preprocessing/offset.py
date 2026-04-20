"""Trim and offset operations for preprocessing."""

import numpy as np
import pandas as pd

from app.services.preprocessing.series_ops import replace_with_numeric_series
from app.services.preprocessing.timing import find_time0_row, get_time_numeric


def trim_dataframe(df, time_column, start_time, end_time):
    """Trim rows by time while keeping the existing time values untouched."""
    start_time = float(start_time)
    end_time = float(end_time)
    if end_time < start_time:
        start_time, end_time = end_time, start_time
    time_arr = get_time_numeric(df, time_column)
    numeric_mask = np.isfinite(time_arr)
    within_range = numeric_mask & (time_arr >= start_time) & (time_arr <= end_time)
    keep_mask = (~numeric_mask) | within_range
    return df.loc[keep_mask].reset_index(drop=True).copy()


def get_offset_sample_rows(df, time_column, sample_count, time0_row=None, include_time0=True):
    """Return offset rows from data start toward Time0."""
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
    """Apply baseline offset to every requested numeric channel."""
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
        replace_with_numeric_series(out, channel_name, corrected)

    return out, offsets
