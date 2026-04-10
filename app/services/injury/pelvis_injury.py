import numpy as np

from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_metric_at, fmt_metric_range
from app.services.injury.common_engines import compute_3ms_bundle
from app.services.preprocessing.service import compute_resultant_xyz


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


def _format_axis_peak_lines(axis_label, unit, time, values):
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
        fmt_metric_at(f'{axis_label} MAX', float(valid_v[max_idx]), unit=unit, time_s=float(valid_t[max_idx])),
        fmt_metric_at(f'{axis_label} MIN', float(valid_v[min_idx]), unit=unit, time_s=float(valid_t[min_idx])),
    ]


def _detail_line(label, unit, detail):
    if not detail or detail.get('value') is None:
        return f'{label}: -'
    return fmt_metric_at(label, detail.get('value'), unit=unit, time_s=detail.get('time_s'))


def _interval_detail_line(label, unit, detail):
    if not detail or detail.get('value') is None:
        return f'{label}: -'
    start_s = detail.get('start_time_s')
    end_s = detail.get('end_time_s')
    if start_s is not None and end_s is not None:
        return fmt_metric_range(label, detail.get('value'), unit=unit, start_s=start_s, end_s=end_s, value_decimals=4)
    return fmt_metric_at(label, detail.get('value'), unit=unit, time_s=detail.get('time_s'))


def calculate_pelvis_injury_bundle(time, x_values, y_values, z_values, plot_unit, use_high_res_cumulative_3ms=True):
    time_arr = np.asarray(time, dtype=float)
    x_arr = np.asarray(x_values, dtype=float)
    y_arr = np.asarray(y_values, dtype=float)
    z_arr = np.asarray(z_values, dtype=float)
    resultant = compute_resultant_xyz(x_arr, y_arr, z_arr)
    peak_3ms_bundle = compute_3ms_bundle(
        time_arr,
        resultant,
        use_abs=True,
        include_res_peak=True,
        use_high_res_cumulative_3ms=use_high_res_cumulative_3ms,
    )
    one_peak_3ms = dict(peak_3ms_bundle.get('one_peak_3ms', {}))
    multiple_peak_3ms = dict(peak_3ms_bundle.get('multiple_peak_3ms', {}))
    resultant_peak = dict(peak_3ms_bundle.get('res_peak', {}))

    summary_lines = []
    for axis_label, arr in (('PELVIS X', x_arr), ('PELVIS Y', y_arr), ('PELVIS Z', z_arr)):
        summary_lines.extend(_format_axis_peak_lines(axis_label, plot_unit, time_arr, arr))
    summary_lines.append('')
    summary_lines.append('- Injuries -')
    summary_lines.append(_interval_detail_line('One Peak 3ms_Clip', plot_unit, one_peak_3ms))
    summary_lines.append(_interval_detail_line('Multiple Peak 3ms_Clip', plot_unit, multiple_peak_3ms))
    summary_lines.append(_detail_line('Res-Peak', plot_unit, resultant_peak))

    return {
        'metrics': {
            'time': time_arr,
            'x_plot': x_arr,
            'y_plot': y_arr,
            'z_plot': z_arr,
            'resultant': resultant,
            'one_peak_3ms': one_peak_3ms,
            'multiple_peak_3ms': multiple_peak_3ms,
            'resultant_peak': resultant_peak,
            'plot_unit': plot_unit,
        },
        'summary_text': '\n'.join(summary_lines),
        'summary_format_version': SUMMARY_FORMAT_VERSION,
    }
