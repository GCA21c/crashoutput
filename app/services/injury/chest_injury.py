import numpy as np

from app.core.utils.formatting import (
    SUMMARY_FORMAT_VERSION,
    fmt_metric_at,
    fmt_metric_range,
    fmt_peak_line,
    fmt_value,
)
from app.services.preprocessing.service import compute_chest_metrics


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



def _peak_line(label, unit, detail, decimals=4):
    if not detail or detail.get('value') is None:
        return f"{label}: -"
    return fmt_metric_at(label, detail.get('value'), unit=unit, time_s=detail.get('time_s'), value_decimals=decimals)


def _clip_line(label, unit, detail, axis_suffix=None):
    if not detail or detail.get('value') is None:
        return f"{label}: -"
    start_s = detail.get('start_time_s')
    end_s = detail.get('end_time_s')
    if start_s is not None and end_s is not None:
        return fmt_metric_range(label, detail.get('value'), unit=unit, start_s=start_s, end_s=end_s, value_decimals=4)
    return fmt_metric_at(label, detail.get('value'), unit=unit, time_s=detail.get('time_s'), value_decimals=4)


def calculate_chest_injury_bundle(
    time,
    x_values,
    y_values,
    z_values,
    disp_values,
    accel_units,
    disp_unit,
    criterion_key,
    raw_displacement,
    raw_accel,
    accel_filter_labels,
    disp_filter_label,
    disp_prefiltered=None,
    vc_sign_pref=1.0,
    use_high_res_cumulative_3ms=True,
):
    metrics = compute_chest_metrics(
        time,
        x_values,
        y_values,
        z_values,
        disp_values,
        accel_units=accel_units,
        disp_unit=disp_unit,
        criterion_key=criterion_key,
        raw_displacement=raw_displacement,
        raw_accel=raw_accel,
        accel_filter_labels=accel_filter_labels,
        disp_filter_label=disp_filter_label,
        disp_prefiltered=disp_prefiltered,
        vc_sign_pref=vc_sign_pref,
        use_high_res_cumulative_3ms=use_high_res_cumulative_3ms,
    )

    lines = []
    for label, arr in (('CHEST X', metrics['x_g']), ('CHEST Y', metrics['y_g']), ('CHEST Z', metrics['z_g'])):
        lines.extend(_format_axis_peak_lines(label, 'g', metrics['time'], arr))
    lines.append('')
    lines.append('- Injuries -')
    lines.append(_clip_line('One Peak 3ms_Clip', 'g', metrics.get('one_peak_3ms_detail')))
    lines.append(_clip_line('Multiple Peak 3ms_Clip', 'g', metrics.get('multiple_peak_3ms_detail')))
    lines.append(_peak_line('Res-Peak', 'g', metrics.get('resultant_peak', {}), decimals=4))
    lines.append('')
    lines.extend(_format_axis_peak_lines('Displacement', 'mm', metrics['time'], metrics.get('displacement_mm', [])))
    lines.append(_peak_line('Displacement Peak', 'mm', metrics.get('displacement_peak', {}), decimals=4))
    lines.append('')
    sae_max = metrics.get('vc_sae_max', {})
    sae_min = metrics.get('vc_sae_min', {})
    ece_max = metrics.get('vc_ece_max', {})
    ece_min = metrics.get('vc_ece_min', {})
    lines.append("V*C SAE J1727_CFC600")
    lines.append(_peak_line('Max', 'm/s', sae_max, decimals=4))
    lines.append(_peak_line('Min', 'm/s', sae_min, decimals=4))
    lines.append('')
    lines.append('V*C ECE94_CFC180')
    lines.append(_peak_line('Max', 'm/s', ece_max, decimals=4))
    lines.append(_peak_line('Min', 'm/s', ece_min, decimals=4))
    crit = metrics.get('criteria', {})
    lines.append('')
    lines.append(f"Dummy: {crit.get('label', criterion_key)}")
    lines.append(f"FMVSS Chest Acc Limit: {crit.get('accel_3ms_limit_g', '-') if crit.get('accel_3ms_limit_g') is not None else '-'} g")
    lines.append(f"FMVSS Chest Deflection Limit: {crit.get('deflection_limit_mm', '-') if crit.get('deflection_limit_mm') is not None else '-'} mm")
    lines.append(f"VC Limit (reference): {crit.get('vc_limit_mps', '-') if crit.get('vc_limit_mps') is not None else '-'} m/s")
    if metrics.get('disp_filter_note'):
        lines.append(metrics['disp_filter_note'])

    return {
        'metrics': metrics,
        'summary_text': '\n'.join(lines),
        'summary_format_version': SUMMARY_FORMAT_VERSION,
    }
