import numpy as np

from app.core.dummy.iliac_dummy_profiles import get_iliac_dummy_profile
from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_time_ms, fmt_value


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


def _peak_abs(values, time):
    arr = np.asarray(values, dtype=float)
    t = np.asarray(time, dtype=float)
    n = min(arr.size, t.size)
    if n <= 0:
        return {'value': np.nan, 'time_s': np.nan, 'index': -1}
    arr = arr[:n]
    t = t[:n]
    valid = np.isfinite(arr) & np.isfinite(t)
    if not np.any(valid):
        return {'value': np.nan, 'time_s': np.nan, 'index': -1}
    valid_idx = np.where(valid)[0]
    local = int(np.argmax(np.abs(arr[valid])))
    idx = int(valid_idx[local])
    return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}


def _peak_max(values, time):
    arr = np.asarray(values, dtype=float)
    t = np.asarray(time, dtype=float)
    n = min(arr.size, t.size)
    if n <= 0:
        return {'value': np.nan, 'time_s': np.nan, 'index': -1}
    arr = arr[:n]
    t = t[:n]
    valid = np.isfinite(arr) & np.isfinite(t)
    if not np.any(valid):
        return {'value': np.nan, 'time_s': np.nan, 'index': -1}
    valid_idx = np.where(valid)[0]
    local = int(np.argmax(arr[valid]))
    idx = int(valid_idx[local])
    return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}


def _peak_min(values, time):
    arr = np.asarray(values, dtype=float)
    t = np.asarray(time, dtype=float)
    n = min(arr.size, t.size)
    if n <= 0:
        return {'value': np.nan, 'time_s': np.nan, 'index': -1}
    arr = arr[:n]
    t = t[:n]
    valid = np.isfinite(arr) & np.isfinite(t)
    if not np.any(valid):
        return {'value': np.nan, 'time_s': np.nan, 'index': -1}
    valid_idx = np.where(valid)[0]
    local = int(np.argmin(arr[valid]))
    idx = int(valid_idx[local])
    return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}


def _resultant(force_n, moment_nm):
    force_n = np.asarray(force_n, dtype=float)
    moment_nm = np.asarray(moment_nm, dtype=float)
    n = min(force_n.size, moment_nm.size)
    if n <= 0:
        return np.asarray([], dtype=float)
    return np.sqrt(np.square(force_n[:n]) + np.square(moment_nm[:n]))


def _side_summary(side_label, force_n, moment_nm, time_s):
    comp = _peak_min(force_n, time_s)
    tens = _peak_max(force_n, time_s)
    moment_max = _peak_max(moment_nm, time_s)
    moment_min = _peak_min(moment_nm, time_s)
    moment = _peak_abs(moment_nm, time_s)
    resultant = _peak_abs(_resultant(force_n, moment_nm), time_s)
    return {
        'side': side_label,
        'compression_force_n': comp['value'],
        'compression_time_s': comp['time_s'],
        'tension_force_n': tens['value'],
        'tension_time_s': tens['time_s'],
        'max_moment_nm': moment_max['value'],
        'max_moment_time_s': moment_max['time_s'],
        'min_moment_nm': moment_min['value'],
        'min_moment_time_s': moment_min['time_s'],
        'peak_moment_nm': moment['value'],
        'peak_moment_time_s': moment['time_s'],
        'combined_resultant': resultant['value'],
        'combined_resultant_time_s': resultant['time_s'],
    }


def calculate_iliac_injury_bundle(
    *,
    time,
    left_fx,
    left_my,
    right_fx,
    right_my,
    left_fx_unit='N',
    left_my_unit='Nm',
    right_fx_unit='N',
    right_my_unit='Nm',
    criterion_key='Thor_50%M',
):
    profile = get_iliac_dummy_profile(criterion_key)
    time_s = np.asarray(time, dtype=float)

    left_force_n = _convert_force_to_n(left_fx, left_fx_unit)
    left_moment_nm = _convert_moment_to_nm(left_my, left_my_unit)
    right_force_n = _convert_force_to_n(right_fx, right_fx_unit)
    right_moment_nm = _convert_moment_to_nm(right_my, right_my_unit)

    left_summary = _side_summary('LEFT', left_force_n, left_moment_nm, time_s)
    right_summary = _side_summary('RIGHT', right_force_n, right_moment_nm, time_s)

    summary_lines = [
        f"ILIAC / ASIS ({profile.get('label')})",
        f"- LEFT Fx compression: {fmt_value(left_summary['compression_force_n'], 1)} N @ {fmt_time_ms(left_summary['compression_time_s'], 1)}",
        f"- LEFT Fx tension: {fmt_value(left_summary['tension_force_n'], 1)} N @ {fmt_time_ms(left_summary['tension_time_s'], 1)}",
        f"- LEFT |My| peak: {fmt_value(left_summary['peak_moment_nm'], 2)} Nm @ {fmt_time_ms(left_summary['peak_moment_time_s'], 1)}",
        f"- LEFT combined √(Fx²+My²): {fmt_value(left_summary['combined_resultant'], 2)} @ {fmt_time_ms(left_summary['combined_resultant_time_s'], 1)}",
        f"- RIGHT Fx compression: {fmt_value(right_summary['compression_force_n'], 1)} N @ {fmt_time_ms(right_summary['compression_time_s'], 1)}",
        f"- RIGHT Fx tension: {fmt_value(right_summary['tension_force_n'], 1)} N @ {fmt_time_ms(right_summary['tension_time_s'], 1)}",
        f"- RIGHT |My| peak: {fmt_value(right_summary['peak_moment_nm'], 2)} Nm @ {fmt_time_ms(right_summary['peak_moment_time_s'], 1)}",
        f"- RIGHT combined √(Fx²+My²): {fmt_value(right_summary['combined_resultant'], 2)} @ {fmt_time_ms(right_summary['combined_resultant_time_s'], 1)}",
        f"- Reference: {profile.get('source')}",
    ]

    metrics = {
        'time': time_s,
        'left_fx_n': left_force_n,
        'left_my_nm': left_moment_nm,
        'right_fx_n': right_force_n,
        'right_my_nm': right_moment_nm,
        'left_fx_my_resultant': _resultant(left_force_n, left_moment_nm),
        'right_fx_my_resultant': _resultant(right_force_n, right_moment_nm),
        'left_summary': left_summary,
        'right_summary': right_summary,
        'plot_force_unit': 'N',
        'plot_moment_unit': 'Nm',
        'criterion_key': criterion_key,
        'criterion_label': profile.get('label'),
        'criterion_source': profile.get('source'),
    }

    return {
        'metrics': metrics,
        'summary_text': '\n'.join(summary_lines),
        'summary_format_version': SUMMARY_FORMAT_VERSION,
    }
