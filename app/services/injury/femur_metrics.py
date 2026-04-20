import numpy as np

from app.core.dummy import get_femur_dummy_profile
from app.services.injury.forces import normalize_force_to_n, peak_detail_abs


def compute_femur_metrics(time_s, left_force_n, right_force_n, criterion_key='H3_50%M', left_unit=None, right_unit=None):
    time_arr = np.asarray(time_s, dtype=float)
    left, left_unit_resolved = normalize_force_to_n(left_force_n, left_unit)
    right, right_unit_resolved = normalize_force_to_n(right_force_n, right_unit)
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

    left_peak_abs = peak_detail_abs(time_arr, left)
    right_peak_abs = peak_detail_abs(time_arr, right)
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
