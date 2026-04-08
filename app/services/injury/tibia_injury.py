import numpy as np

from app.core.dummy.tibia_dummy_profiles import get_tibia_dummy_profile
from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_metric_at, fmt_value


_FORCE_UNIT_FACTORS = {
    'n': 1.0,
    'kn': 1000.0,
    'lb': 4.4482216152605,
    'lbf': 4.4482216152605,
}

_MOMENT_UNIT_FACTORS = {
    'nm': 1.0,
    'n*m': 1.0,
    'knm': 1000.0,
    'kn*m': 1000.0,
    'lbf*ft': 1.3558179483314004,
    'lb*ft': 1.3558179483314004,
    'lbf*in': 0.1129848290276167,
    'lb*in': 0.1129848290276167,
}


def _unit_key(unit_text):
    return str(unit_text or '').strip().lower().replace(' ', '')


def _convert_force_to_n(values, unit_text):
    factor = _FORCE_UNIT_FACTORS.get(_unit_key(unit_text), 1.0)
    return np.asarray(values, dtype=float) * factor


def _convert_moment_to_nm(values, unit_text):
    factor = _MOMENT_UNIT_FACTORS.get(_unit_key(unit_text), 1.0)
    return np.asarray(values, dtype=float) * factor


def _peak_detail(time_s, values, mode='max'):
    t = np.asarray(time_s, dtype=float)
    arr = np.asarray(values, dtype=float)
    n = min(t.size, arr.size)
    if n <= 0:
        return {'value': None, 'time_s': None, 'index': None}
    t = t[:n]
    arr = arr[:n]
    valid = np.isfinite(t) & np.isfinite(arr)
    if not np.any(valid):
        return {'value': None, 'time_s': None, 'index': None}
    idx_all = np.flatnonzero(valid)
    vals = arr[idx_all]
    idx_local = int(np.nanargmax(vals) if mode == 'max' else np.nanargmin(vals))
    idx = int(idx_all[idx_local])
    return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}


def _build_station_metrics(time_s, fz_n, mx_nm, my_nm, profile, station):
    fz_n = np.asarray(fz_n, dtype=float)
    mx_nm = np.asarray(mx_nm, dtype=float)
    my_nm = np.asarray(my_nm, dtype=float)
    n = min(len(time_s), len(fz_n), len(mx_nm), len(my_nm))
    t = np.asarray(time_s, dtype=float)[:n]
    fz_n = fz_n[:n]
    mx_nm = mx_nm[:n]
    my_nm = my_nm[:n]

    adjust_key = 'upper_ap_adjust_m_per_n' if station == 'upper' else 'lower_ap_adjust_m_per_n'
    ap_adjust = float(profile.get(adjust_key) or 0.0)
    my_adjusted_nm = my_nm + (fz_n * ap_adjust)
    moment_resultant_nm = np.sqrt(np.square(mx_nm) + np.square(my_adjusted_nm))
    compressive_force_n = np.maximum(-fz_n, 0.0)
    force_crit_n = float(profile.get('force_crit_n') or 1.0)
    moment_crit_nm = float(profile.get('moment_crit_nm') or 1.0)
    tibia_index = (compressive_force_n / force_crit_n) + (moment_resultant_nm / moment_crit_nm)

    return {
        'fz_n': fz_n,
        'mx_nm': mx_nm,
        'my_nm': my_nm,
        'my_adjusted_nm': my_adjusted_nm,
        'moment_resultant_nm': moment_resultant_nm,
        'compressive_force_n': compressive_force_n,
        'tibia_index': tibia_index,
        'peak_tibia_index': _peak_detail(t, tibia_index, mode='max'),
        'peak_compression': _peak_detail(t, compressive_force_n, mode='max'),
        'peak_moment_resultant': _peak_detail(t, moment_resultant_nm, mode='max'),
    }


def _summary_line(prefix, detail, unit=''):
    return fmt_metric_at(prefix, detail.get('value'), unit=unit, time_s=detail.get('time_s'))


def calculate_tibia_injury_bundle(
    *,
    time,
    left_upper_fz,
    left_upper_mx,
    left_upper_my,
    left_lower_fz,
    left_lower_mx,
    left_lower_my,
    right_upper_fz,
    right_upper_mx,
    right_upper_my,
    right_lower_fz,
    right_lower_mx,
    right_lower_my,
    criterion_key='H3_50%M',
    units=None,
):
    profile = get_tibia_dummy_profile(criterion_key)
    units = dict(units or {})
    time_s = np.asarray(time, dtype=float)

    converted = {
        'left_upper_fz': _convert_force_to_n(left_upper_fz, units.get('left_upper_fz', 'N')),
        'left_upper_mx': _convert_moment_to_nm(left_upper_mx, units.get('left_upper_mx', 'Nm')),
        'left_upper_my': _convert_moment_to_nm(left_upper_my, units.get('left_upper_my', 'Nm')),
        'left_lower_fz': _convert_force_to_n(left_lower_fz, units.get('left_lower_fz', 'N')),
        'left_lower_mx': _convert_moment_to_nm(left_lower_mx, units.get('left_lower_mx', 'Nm')),
        'left_lower_my': _convert_moment_to_nm(left_lower_my, units.get('left_lower_my', 'Nm')),
        'right_upper_fz': _convert_force_to_n(right_upper_fz, units.get('right_upper_fz', 'N')),
        'right_upper_mx': _convert_moment_to_nm(right_upper_mx, units.get('right_upper_mx', 'Nm')),
        'right_upper_my': _convert_moment_to_nm(right_upper_my, units.get('right_upper_my', 'Nm')),
        'right_lower_fz': _convert_force_to_n(right_lower_fz, units.get('right_lower_fz', 'N')),
        'right_lower_mx': _convert_moment_to_nm(right_lower_mx, units.get('right_lower_mx', 'Nm')),
        'right_lower_my': _convert_moment_to_nm(right_lower_my, units.get('right_lower_my', 'Nm')),
    }

    left_upper = _build_station_metrics(time_s, converted['left_upper_fz'], converted['left_upper_mx'], converted['left_upper_my'], profile, 'upper')
    left_lower = _build_station_metrics(time_s, converted['left_lower_fz'], converted['left_lower_mx'], converted['left_lower_my'], profile, 'lower')
    right_upper = _build_station_metrics(time_s, converted['right_upper_fz'], converted['right_upper_mx'], converted['right_upper_my'], profile, 'upper')
    right_lower = _build_station_metrics(time_s, converted['right_lower_fz'], converted['right_lower_mx'], converted['right_lower_my'], profile, 'lower')

    peak_candidates = {
        'LEFT UPPER': left_upper['peak_tibia_index'],
        'LEFT LOWER': left_lower['peak_tibia_index'],
        'RIGHT UPPER': right_upper['peak_tibia_index'],
        'RIGHT LOWER': right_lower['peak_tibia_index'],
    }
    overall_label = max(
        peak_candidates,
        key=lambda key: float('-inf') if peak_candidates[key].get('value') is None else peak_candidates[key]['value'],
    )
    overall_peak = peak_candidates[overall_label]

    summary_lines = [
        f"TIBIA ({profile.get('label')})",
        _summary_line('Left Upper Tibia Index', left_upper['peak_tibia_index']),
        _summary_line('Left Lower Tibia Index', left_lower['peak_tibia_index']),
        _summary_line('Right Upper Tibia Index', right_upper['peak_tibia_index']),
        _summary_line('Right Lower Tibia Index', right_lower['peak_tibia_index']),
        '',
        _summary_line('Left Upper Compression', left_upper['peak_compression'], unit='N'),
        _summary_line('Left Lower Compression', left_lower['peak_compression'], unit='N'),
        _summary_line('Right Upper Compression', right_upper['peak_compression'], unit='N'),
        _summary_line('Right Lower Compression', right_lower['peak_compression'], unit='N'),
        '',
        _summary_line('Left Upper Moment Resultant', left_upper['peak_moment_resultant'], unit='Nm'),
        _summary_line('Left Lower Moment Resultant', left_lower['peak_moment_resultant'], unit='Nm'),
        _summary_line('Right Upper Moment Resultant', right_upper['peak_moment_resultant'], unit='Nm'),
        _summary_line('Right Lower Moment Resultant', right_lower['peak_moment_resultant'], unit='Nm'),
        '',
        f"Overall Peak TI: {fmt_value(overall_peak.get('value'))} at {overall_label}",
        f"Reference Lines: TI={fmt_value(profile.get('ti_reference_line'))}, Secondary={fmt_value(profile.get('ti_secondary_line'))}",
        f"Reference: {profile.get('source')}",
    ]

    metrics = {
        'time': time_s,
        'criterion_key': criterion_key,
        'criterion_label': profile.get('label'),
        'criterion_source': profile.get('source'),
        'force_crit_n': float(profile.get('force_crit_n') or 0.0),
        'moment_crit_nm': float(profile.get('moment_crit_nm') or 0.0),
        'ti_reference_line': float(profile.get('ti_reference_line') or 1.0),
        'ti_secondary_line': float(profile.get('ti_secondary_line') or 1.3),
        'left_upper': left_upper,
        'left_lower': left_lower,
        'right_upper': right_upper,
        'right_lower': right_lower,
        'overall_peak_label': overall_label,
        'overall_peak_tibia_index': overall_peak,
        'plot_force_unit': 'N',
        'plot_moment_unit': 'Nm',
    }

    return {
        'metrics': metrics,
        'summary_text': '\n'.join(summary_lines),
        'summary_format_version': SUMMARY_FORMAT_VERSION,
    }
