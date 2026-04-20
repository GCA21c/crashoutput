import numpy as np


def normalize_force_to_n(values, unit_text):
    arr = np.asarray(values, dtype=float)
    unit = str(unit_text or '').strip().lower().replace(' ', '')
    if unit in ('kn', 'kilonewton', 'kilonewtons'):
        return arr * 1000.0, 'N'
    if unit in ('mn',):
        return arr * 1_000_000.0, 'N'
    if unit in ('lbf', 'lb', 'lbs', 'poundforce', 'poundsforce'):
        return arr * 4.4482216152605, 'N'
    return arr, ('N' if not unit else str(unit_text or ''))


def peak_detail_abs(time_arr, values):
    t = np.asarray(time_arr, dtype=float)
    y = np.asarray(values, dtype=float)
    valid = np.isfinite(t) & np.isfinite(y)
    if not np.any(valid):
        return {'value': None, 'time_s': None, 'index': None}
    idx = np.flatnonzero(valid)
    peak_local = int(np.nanargmax(np.abs(y[idx])))
    peak_index = int(idx[peak_local])
    return {'value': float(abs(y[peak_index])), 'time_s': float(t[peak_index]), 'index': peak_index}
