import numpy as np

from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_metric_at


# Research note:
# In practice the Hybrid III knee slider output used in frontal crash analysis is
# handled as a direct displacement channel for each side. For this program's KNEE
# module we compute left/right peak slider displacement and its occurrence time
# from the provided knee slider channels, preserving units from the source data.
# This keeps the implementation aligned with the existing workbench pattern where
# a selected physical channel is analyzed without altering other injury modules.


def _peak_abs_detail(time_arr, values):
    t = np.asarray(time_arr, dtype=float)
    y = np.asarray(values, dtype=float)
    n = min(len(t), len(y))
    if n <= 0:
        return {'value': None, 'time_s': None, 'index': None, 'signed_value': None}
    t = t[:n]
    y = y[:n]
    mask = np.isfinite(t) & np.isfinite(y)
    if not np.any(mask):
        return {'value': None, 'time_s': None, 'index': None, 'signed_value': None}
    valid_idx = np.flatnonzero(mask)
    valid_y = y[valid_idx]
    local = int(np.nanargmax(np.abs(valid_y)))
    idx = int(valid_idx[local])
    return {
        'value': float(abs(y[idx])),
        'time_s': float(t[idx]),
        'index': idx,
        'signed_value': float(y[idx]),
    }


def calculate_knee_injury_bundle(time, left_slider, right_slider, left_unit='', right_unit=''):
    time_arr = np.asarray(time, dtype=float)
    left_arr = np.asarray(left_slider, dtype=float)
    right_arr = np.asarray(right_slider, dtype=float)

    left_peak = _peak_abs_detail(time_arr, left_arr)
    right_peak = _peak_abs_detail(time_arr, right_arr)
    unit = str(left_unit or right_unit or 'mm').strip() or 'mm'

    lines = [
        fmt_metric_at('Left Knee Slider Peak', left_peak.get('value'), unit=unit, time_s=left_peak.get('time_s')),
        fmt_metric_at('Right Knee Slider Peak', right_peak.get('value'), unit=unit, time_s=right_peak.get('time_s')),
    ]

    return {
        'metrics': {
            'time': time_arr,
            'left_slider': left_arr,
            'right_slider': right_arr,
            'left_peak': left_peak,
            'right_peak': right_peak,
            'plot_unit': unit,
        },
        'summary_text': '\n'.join(lines),
        'summary_format_version': SUMMARY_FORMAT_VERSION,
    }
