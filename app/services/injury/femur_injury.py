import numpy as np

from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_metric_at, fmt_value
from app.services.preprocessing.service import compute_femur_metrics


def _global_peak_index(arr, mode='max'):
    values = np.asarray(arr, dtype=float)
    finite = np.flatnonzero(np.isfinite(values))
    if finite.size == 0:
        return None
    valid_values = values[finite]
    target = np.nanmax(valid_values) if mode == 'max' else np.nanmin(valid_values)
    hits = finite[np.isclose(values[finite], target, rtol=1e-12, atol=1e-12)]
    return int(hits[-1]) if hits.size else int(finite[-1])


def _time_value_valid_mask(time_arr, values):
    t = np.asarray(time_arr, dtype=float)
    v = np.asarray(values, dtype=float)
    n = min(len(t), len(v))
    if n <= 0:
        return np.array([], dtype=bool), t[:0], v[:0]
    t2 = t[:n]
    v2 = v[:n]
    return np.isfinite(t2) & np.isfinite(v2), t2, v2


def _format_force_lines(axis_label, time, values):
    mask, arr_t, arr_v = _time_value_valid_mask(time, values)
    if mask.size == 0 or not np.any(mask):
        return [f'{axis_label} MAX: -', f'{axis_label} MIN: -']
    valid_t = arr_t[mask]
    valid_v = arr_v[mask]
    max_idx = _global_peak_index(valid_v, 'max')
    min_idx = _global_peak_index(valid_v, 'min')
    if max_idx is None or min_idx is None:
        return [f'{axis_label} MAX: -', f'{axis_label} MIN: -']
    return [
        fmt_metric_at(f'{axis_label} MAX', float(valid_v[max_idx]), unit='N', time_s=float(valid_t[max_idx])),
        fmt_metric_at(f'{axis_label} MIN', float(valid_v[min_idx]), unit='N', time_s=float(valid_t[min_idx])),
    ]


def calculate_femur_injury_bundle(
    time,
    left_force,
    right_force,
    criterion_key,
    left_unit='',
    right_unit='',
):
    metrics = compute_femur_metrics(
        time_s=time,
        left_force_n=left_force,
        right_force_n=right_force,
        criterion_key=criterion_key,
        left_unit=left_unit,
        right_unit=right_unit,
    )

    crit = metrics.get('criteria', {})
    left_peak = metrics.get('left_peak_abs', {})
    right_peak = metrics.get('right_peak_abs', {})
    lines = []
    lines.extend(_format_force_lines('FEMUR LEFT', metrics['time'], metrics.get('left_force_n', [])))
    lines.extend(_format_force_lines('FEMUR RIGHT', metrics['time'], metrics.get('right_force_n', [])))
    lines.append('')
    lines.append('- Injuries -')
    lines.append(fmt_metric_at('Left Peak Axial Force', left_peak.get('value'), unit='N', time_s=left_peak.get('time_s')))
    lines.append(fmt_metric_at('Right Peak Axial Force', right_peak.get('value'), unit='N', time_s=right_peak.get('time_s')))
    lines.append(f"FMVSS Femur Limit: {fmt_value(crit.get('femur_force_limit_n'), 'N')}")
    lines.append(f"Required Filter: CFC {crit.get('required_cfc', 600)}")
    lines.append(f"Limit Check: {'PASS' if metrics.get('passes_limit') else 'FAIL'}")

    return {
        'metrics': metrics,
        'summary_text': '\n'.join(lines),
        'summary_format_version': SUMMARY_FORMAT_VERSION,
    }
