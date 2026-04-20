"""Dataframe series write helpers used by preprocessing operations."""

import numpy as np


def replace_with_numeric_series(out, channel_name, values):
    """Preserve original CSV structure and metadata rows while writing values."""
    original = out[channel_name].copy()
    result = original.astype(object)
    numeric_values = np.asarray(values, dtype=float)
    finite_mask = np.isfinite(numeric_values)
    if finite_mask.any():
        result.iloc[np.flatnonzero(finite_mask)] = numeric_values[finite_mask].tolist()
    out[channel_name] = result
