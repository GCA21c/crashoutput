import numpy as np

from app.core.utils.formatting import (
    SUMMARY_FORMAT_VERSION,
    fmt_metric_at,
    fmt_metric_range,
    fmt_time_ms,
    fmt_value,
)
from app.services.preprocessing.service import compute_hic_details
from app.services.injury.common_engines import compute_3ms_bundle



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

    max_time = float(valid_t[max_idx])
    min_time = float(valid_t[min_idx])
    max_value = float(valid_v[max_idx])
    min_value = float(valid_v[min_idx])
    return [
        fmt_metric_at(f'{axis_label} MAX', max_value, unit=unit, time_s=max_time),
        fmt_metric_at(f'{axis_label} MIN', min_value, unit=unit, time_s=min_time),
    ]


def _interval_metric_line(label, unit, detail, decimals=4):
    if not detail or detail.get('value') is None:
        return f'{label}: -'
    return fmt_metric_range(
        label,
        detail["value"],
        unit=unit,
        start_s=detail.get("start_time_s"),
        end_s=detail.get("end_time_s"),
        value_decimals=decimals,
    )


def _hic_metric_line(label, detail, decimals=4):
    if not detail or detail.get('value') is None:
        return f'{label}: -'
    return fmt_metric_range(
        label,
        detail["value"],
        start_s=detail.get("start_time"),
        end_s=detail.get("end_time"),
        value_decimals=decimals,
    )


def _peak_metric_line(label, unit, detail, decimals=4):
    if not detail or detail.get('value') is None:
        return f'{label}: -'
    return fmt_metric_at(label, detail["value"], unit=unit, time_s=detail.get("time_s"), value_decimals=decimals)



def build_head_injury_bundle(
    time,
    resultant_g,
    x_plot,
    y_plot,
    z_plot,
    plot_unit,
    channels,
    resultant_channel=None,
    resultant_filter_label=None,
    high_res_3ms_sliding_window=True,
):
    time_arr = np.asarray(time, dtype=float)
    resultant_arr = np.asarray(resultant_g, dtype=float)
    x_arr = np.asarray(x_plot, dtype=float)
    y_arr = np.asarray(y_plot, dtype=float)
    z_arr = np.asarray(z_plot, dtype=float)

    hic15 = compute_hic_details(time_arr, resultant_arr, max_window_s=0.015)
    hic36 = compute_hic_details(time_arr, resultant_arr, max_window_s=0.036)
    peak_3ms_bundle = compute_3ms_bundle(
        time_arr,
        resultant_arr,
        use_abs=True,
        include_res_peak=True,
        high_res_sliding_window=high_res_3ms_sliding_window,
    )
    one_peak_3ms = peak_3ms_bundle.get('one_peak_3ms', {})
    multiple_peak_3ms = peak_3ms_bundle.get('multiple_peak_3ms', {})
    resultant_peak = peak_3ms_bundle.get('res_peak', {})

    if all(item is None for item in (hic15, hic36)) and not one_peak_3ms.get('value') and not multiple_peak_3ms.get('value'):
        raise ValueError('계산 가능한 구간이 없습니다.')

    bundle = {
        'time': time_arr,
        'resultant_g': resultant_arr,
        'x_plot': x_arr,
        'y_plot': y_arr,
        'z_plot': z_arr,
        'channels': tuple(channels),
        'plot_unit': plot_unit,
        'resultant_channel': resultant_channel,
        'resultant_filter_label': resultant_filter_label,
        'hic15': hic15,
        'hic36': hic36,
        'one_peak_3ms': one_peak_3ms,
        'multiple_peak_3ms': multiple_peak_3ms,
        'peak_3ms_bundle': peak_3ms_bundle,
        'resultant_peak': resultant_peak,
        'clip3': one_peak_3ms.get('value'),
    }

    hic15_text = _hic_metric_line('HIC15', hic15)
    hic36_text = _hic_metric_line('HIC36', hic36)
    clip3_text = _interval_metric_line('One Peak 3ms_Clip', plot_unit, one_peak_3ms)

    summary_lines = []
    for axis_label, arr in (('HEAD X', x_arr), ('HEAD Y', y_arr), ('HEAD Z', z_arr), ('HEAD Resultant', resultant_arr)):
        summary_lines.extend(_format_axis_peak_lines(axis_label, plot_unit, time_arr, arr))
    summary_lines.append('')
    summary_lines.append('- Injuries -')
    summary_lines.append(_hic_metric_line('HIC15', hic15))
    summary_lines.append(_hic_metric_line('HIC36', hic36))
    summary_lines.append(_interval_metric_line('One Peak 3ms_Clip', plot_unit, one_peak_3ms))
    summary_lines.append(_interval_metric_line('Multiple Peak 3ms_Clip', plot_unit, multiple_peak_3ms))
    summary_lines.append(_peak_metric_line('Res-Peak', plot_unit, resultant_peak))
    summary_text = '\n'.join(summary_lines) if summary_lines else '-'

    metadata = {
        'summary_text': summary_text,
        'summary_format_version': SUMMARY_FORMAT_VERSION,
        'plot_unit': plot_unit,
        'resultant_channel': resultant_channel,
        'resultant_filter_label': resultant_filter_label,
        'channels': list(channels),
        'resultant_channel': resultant_channel,
        'resultant_filter_label': resultant_filter_label,
        'hic15_value': float(hic15['value']) if hic15 is not None else None,
        'hic15_start_time_s': float(hic15['start_time']) if hic15 is not None else None,
        'hic15_end_time_s': float(hic15['end_time']) if hic15 is not None else None,
        'hic36_value': float(hic36['value']) if hic36 is not None else None,
        'hic36_start_time_s': float(hic36['start_time']) if hic36 is not None else None,
        'hic36_end_time_s': float(hic36['end_time']) if hic36 is not None else None,
        'one_peak_3ms_value': float(one_peak_3ms['value']) if one_peak_3ms.get('value') is not None else None,
        'one_peak_3ms_start_time_s': float(one_peak_3ms['start_time_s']) if one_peak_3ms.get('start_time_s') is not None else None,
        'one_peak_3ms_end_time_s': float(one_peak_3ms['end_time_s']) if one_peak_3ms.get('end_time_s') is not None else None,
        'multiple_peak_3ms_value': float(multiple_peak_3ms['value']) if multiple_peak_3ms.get('value') is not None else None,
        'multiple_peak_3ms_start_time_s': float(multiple_peak_3ms['start_time_s']) if multiple_peak_3ms.get('start_time_s') is not None else None,
        'multiple_peak_3ms_end_time_s': float(multiple_peak_3ms['end_time_s']) if multiple_peak_3ms.get('end_time_s') is not None else None,
        'resultant_peak_value': float(resultant_peak['value']) if resultant_peak.get('value') is not None else None,
        'resultant_peak_time_s': float(resultant_peak['time_s']) if resultant_peak.get('time_s') is not None else None,
        'clip3_value': float(one_peak_3ms['value']) if one_peak_3ms.get('value') is not None else None,
    }

    for axis_name, arr in (('head_x', x_arr), ('head_y', y_arr), ('head_z', z_arr), ('head_resultant', resultant_arr)):
        mask, arr_t, arr_v = _time_value_valid_mask(time_arr, arr)
        if mask.size == 0 or not np.any(mask):
            metadata[f'{axis_name}_max_value'] = None
            metadata[f'{axis_name}_max_time_s'] = None
            metadata[f'{axis_name}_min_value'] = None
            metadata[f'{axis_name}_min_time_s'] = None
            continue
        vt = arr_t[mask]
        vv = arr_v[mask]
        i_max = _global_peak_index(vv, 'max')
        i_min = _global_peak_index(vv, 'min')
        metadata[f'{axis_name}_max_value'] = float(vv[i_max]) if i_max is not None else None
        metadata[f'{axis_name}_max_time_s'] = float(vt[i_max]) if i_max is not None else None
        metadata[f'{axis_name}_min_value'] = float(vv[i_min]) if i_min is not None else None
        metadata[f'{axis_name}_min_time_s'] = float(vt[i_min]) if i_min is not None else None

    history_text = 'Head injury calculated'
    if hic15 is not None or hic36 is not None:
        hic15_txt = f"{hic15['value']:.4f}" if hic15 is not None else 'NA'
        hic36_txt = f"{hic36['value']:.4f}" if hic36 is not None else 'NA'
        history_text = f'Head injury calculated: HIC15={hic15_txt}, HIC36={hic36_txt}'

    return {
        'bundle': bundle,
        'summary_text': summary_text,
        'summary_format_version': SUMMARY_FORMAT_VERSION,
        'hic15_text': hic15_text,
        'hic36_text': hic36_text,
        'clip3_text': clip3_text,
        'metadata': metadata,
        'history_text': history_text,
    }
