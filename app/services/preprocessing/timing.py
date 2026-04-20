"""Numeric channel and time-axis helpers for preprocessing."""

import numpy as np
import pandas as pd


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
    nonneg = np.flatnonzero(times >= 0.0)
    if nonneg.size:
        return int(valid_rows[nonneg[0]])
    nearest = int(np.argmin(np.abs(times)))
    return int(valid_rows[nearest])


def get_sample_rate(time_arr):
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
