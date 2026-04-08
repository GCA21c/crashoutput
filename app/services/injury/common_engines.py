import numpy as np


def _resultant_peak_detail(time_s, signal, use_abs=False):
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(signal, dtype=float)
    n = min(len(t), len(y))
    if n <= 0:
        return {'value': None, 'time_s': None, 'index': None}
    t = t[:n]
    y = y[:n]
    mask = np.isfinite(t) & np.isfinite(y)
    if not np.any(mask):
        return {'value': None, 'time_s': None, 'index': None}
    valid_t = t[mask]
    valid_y = np.abs(y[mask]) if use_abs else y[mask]
    target = np.nanmax(valid_y)
    hits = np.flatnonzero(np.isclose(valid_y, target, rtol=1e-12, atol=1e-12))
    idx_local = int(hits[-1]) if hits.size else int(np.nanargmax(valid_y))
    return {
        'value': float(valid_y[idx_local]),
        'time_s': float(valid_t[idx_local]),
        'index': idx_local,
    }


def compute_3ms_bundle(time_s, signal, use_abs=True, window_s=0.003, include_res_peak=True):
    from app.services.preprocessing.service import (
        compute_3ms_one_peak_exceedance_details,
        compute_3ms_multiple_peak_exceedance_details,
    )

    one_peak = dict(compute_3ms_one_peak_exceedance_details(time_s, signal, use_abs=use_abs, window_s=window_s) or {})
    multiple_peak = dict(compute_3ms_multiple_peak_exceedance_details(time_s, signal, use_abs=use_abs, window_s=window_s) or {})
    out = {
        'one_peak_3ms': one_peak,
        'multiple_peak_3ms': multiple_peak,
    }
    if include_res_peak:
        out['res_peak'] = _resultant_peak_detail(time_s, signal, use_abs=use_abs)
    return out


compute_3ms_result_bundle = compute_3ms_bundle


def compute_3ms_engine_detail(time_s, signal, use_abs=True, window_s=0.003):
    bundle = compute_3ms_bundle(time_s, signal, use_abs=use_abs, window_s=window_s, include_res_peak=False)
    return bundle.get('one_peak_3ms', {})


def _gradient_contiguous(time_arr, values, method='five_point'):
    time_arr = np.asarray(time_arr, dtype=float)
    values = np.asarray(values, dtype=float)
    out = np.full_like(values, np.nan, dtype=float)
    valid = np.isfinite(time_arr) & np.isfinite(values)
    if not np.any(valid):
        return out
    idx = np.flatnonzero(valid)
    split_points = np.where(np.diff(idx) > 1)[0] + 1
    groups = np.split(idx, split_points)
    for grp in groups:
        if grp.size < 3:
            continue
        seg_t = time_arr[grp]
        seg_y = values[grp]
        dt = np.diff(seg_t)
        uniform = dt.size > 0 and np.all(np.isfinite(dt)) and np.all(dt > 0) and np.allclose(dt, np.median(dt), rtol=1e-6, atol=1e-12)
        if method == 'five_point' and grp.size >= 5 and uniform:
            h = float(np.median(dt))
            grad = np.full_like(seg_y, np.nan, dtype=float)
            grad[2:-2] = (-seg_y[4:] + 8.0 * seg_y[3:-1] - 8.0 * seg_y[1:-3] + seg_y[:-4]) / (12.0 * h)
            grad[0] = (-25.0 * seg_y[0] + 48.0 * seg_y[1] - 36.0 * seg_y[2] + 16.0 * seg_y[3] - 3.0 * seg_y[4]) / (12.0 * h)
            grad[1] = (-3.0 * seg_y[0] - 10.0 * seg_y[1] + 18.0 * seg_y[2] - 6.0 * seg_y[3] + seg_y[4]) / (12.0 * h)
            grad[-2] = (3.0 * seg_y[-1] + 10.0 * seg_y[-2] - 18.0 * seg_y[-3] + 6.0 * seg_y[-4] - seg_y[-5]) / (12.0 * h)
            grad[-1] = (25.0 * seg_y[-1] - 48.0 * seg_y[-2] + 36.0 * seg_y[-3] - 16.0 * seg_y[-4] + 3.0 * seg_y[-5]) / (12.0 * h)
        else:
            grad = np.gradient(seg_y, seg_t, edge_order=2)
            grad[0] = grad[1]
            grad[-1] = grad[-2]
        out[grp] = grad
    return out


def _suppress_edge_pulse(series):
    arr = np.asarray(series, dtype=float).copy()
    finite_idx = np.flatnonzero(np.isfinite(arr))
    if finite_idx.size >= 3:
        arr[finite_idx[0]] = arr[finite_idx[1]]
        arr[finite_idx[-1]] = arr[finite_idx[-2]]
    return arr


def _extrema_times(time_s, series):
    t = np.asarray(time_s, dtype=float)
    arr = np.asarray(series, dtype=float)
    mask = np.isfinite(t) & np.isfinite(arr)
    if not np.any(mask):
        return None, None
    valid_idx = np.flatnonzero(mask)
    sv = arr[valid_idx]
    return float(t[int(valid_idx[int(np.nanargmax(sv))])]), float(t[int(valid_idx[int(np.nanargmin(sv))])])


def _strict_peak_detail(time_s, series, mode='max'):
    t = np.asarray(time_s, dtype=float)
    arr = np.asarray(series, dtype=float)
    mask = np.isfinite(t) & np.isfinite(arr)
    if not np.any(mask):
        return {'value': None, 'time_s': None, 'index': None}
    valid_idx = np.flatnonzero(mask)
    valid_arr = arr[valid_idx]
    idx_local = int(np.nanargmax(valid_arr) if mode == 'max' else np.nanargmin(valid_arr))
    idx = int(valid_idx[idx_local])
    return {'value': float(arr[idx]), 'time_s': float(t[idx]), 'index': idx}


def _refined_peak_detail(time_s, series, mode='max'):
    strict = _strict_peak_detail(time_s, series, mode=mode)
    idx = strict.get('index')
    if idx is None:
        return strict
    t = np.asarray(time_s, dtype=float)
    arr = np.asarray(series, dtype=float)
    if idx <= 0 or idx >= len(arr) - 1:
        return strict
    y0, y1, y2 = arr[idx - 1], arr[idx], arr[idx + 1]
    x0, x1, x2 = t[idx - 1], t[idx], t[idx + 1]
    if not all(np.isfinite(v) for v in (y0, y1, y2, x0, x1, x2)):
        return strict
    dt1 = x1 - x0
    dt2 = x2 - x1
    if dt1 <= 0 or dt2 <= 0 or not np.isclose(dt1, dt2, rtol=1e-6, atol=1e-12):
        return strict
    h = float((dt1 + dt2) * 0.5)
    denom = (y0 - 2.0 * y1 + y2)
    if abs(denom) < 1e-18:
        return strict
    delta = 0.5 * (y0 - y2) / denom
    if not np.isfinite(delta) or abs(delta) > 1.0:
        return strict
    peak_time = float(x1 + delta * h)
    peak_value = float(y1 - 0.25 * (y0 - y2) * delta)
    return {'value': peak_value, 'time_s': peak_time, 'index': idx}


def _representative_cluster_peak(time_s, series, mode='max', cluster_window_s=0.020, close_ratio=0.97):
    t = np.asarray(time_s, dtype=float)
    arr = np.asarray(series, dtype=float)
    mask = np.isfinite(t) & np.isfinite(arr)
    if not np.any(mask):
        return {'value': None, 'time_s': None, 'index': None}
    valid_idx = np.flatnonzero(mask)
    a = arr[valid_idx]
    if a.size < 3:
        return _strict_peak_detail(t, arr, mode=mode)
    if mode == 'max':
        peak_mask = (a[1:-1] >= a[:-2]) & (a[1:-1] >= a[2:])
        cand = valid_idx[1:-1][peak_mask & np.isfinite(a[1:-1])]
        if cand.size == 0:
            return _refined_peak_detail(t, arr, mode='max')
        global_peak = float(np.nanmax(arr[mask]))
        threshold = global_peak * float(close_ratio)
        cand = cand[arr[cand] >= threshold]
    else:
        peak_mask = (a[1:-1] <= a[:-2]) & (a[1:-1] <= a[2:])
        cand = valid_idx[1:-1][peak_mask & np.isfinite(a[1:-1])]
        if cand.size == 0:
            return _refined_peak_detail(t, arr, mode='min')
        global_peak = float(np.nanmin(arr[mask]))
        threshold = global_peak * float(close_ratio)
        cand = cand[arr[cand] <= threshold]
    if cand.size == 0:
        return _refined_peak_detail(t, arr, mode=mode)
    cand = np.sort(cand)
    clusters = [[int(cand[0])]]
    for idx in cand[1:]:
        if (t[int(idx)] - t[clusters[-1][-1]]) <= float(cluster_window_s):
            clusters[-1].append(int(idx))
        else:
            clusters.append([int(idx)])
    def cluster_score(cluster):
        vals = np.asarray([arr[i] for i in cluster], dtype=float)
        return float(np.nanmax(vals)) if mode == 'max' else float(np.abs(np.nanmin(vals)))
    best_cluster = max(clusters, key=cluster_score)
    chosen = int(best_cluster[-1])
    return {'value': float(arr[chosen]), 'time_s': float(t[chosen]), 'index': chosen}


def compute_vc_engine_bundle(time_s, disp_mm, preset, sign_pref=1.0, filter_meta=None, display_mode='strict', user_direction_mode=True):
    t = np.asarray(time_s, dtype=float)
    disp_source_mm = np.asarray(disp_mm, dtype=float)
    disp_m = disp_source_mm / 1000.0
    depth_m = float(preset.get('dummy_constant_mm', 229.0)) / 1000.0
    scaling = float(preset.get('scaling_factor', 1.0) or 1.0)

    vel_regulatory_mps = _gradient_contiguous(t, disp_m, method='five_point')
    vc_regulatory = scaling * ((float(sign_pref) * disp_m) / depth_m) * vel_regulatory_mps

    sign_display = float(sign_pref)
    sign_flip_applied = False
    if bool(user_direction_mode):
        vc_display = vc_regulatory
        display_max = _strict_peak_detail(t, vc_display, mode='max')
        display_min = _strict_peak_detail(t, vc_display, mode='min')
    else:
        vc_display = _suppress_edge_pulse(vc_regulatory)
        tmax, tmin = _extrema_times(t, vc_display)
        if tmax is not None and tmin is not None and tmax > tmin:
            sign_display = -sign_display
            vc_display = -vc_display
            sign_flip_applied = True

        if str(display_mode or 'cluster') == 'cluster':
            display_max = _representative_cluster_peak(t, vc_display, mode='max')
            display_min = _representative_cluster_peak(t, vc_display, mode='min')
        else:
            display_max = _refined_peak_detail(t, vc_display, mode='max')
            display_min = _refined_peak_detail(t, vc_display, mode='min')

    regulatory_max = _strict_peak_detail(t, vc_regulatory, mode='max')
    regulatory_min = _strict_peak_detail(t, vc_regulatory, mode='min')

    return {
        'disp_filtered_mm': disp_source_mm,
        'vel_regulatory_mps': vel_regulatory_mps,
        'vel_filtered_mps': vel_regulatory_mps,
        'vel_raw_mps': vel_regulatory_mps,
        'vc_regulatory': vc_regulatory,
        'vc_display': vc_display,
        'vc_raw': vc_regulatory,
        'vc': vc_regulatory,
        'sign': float(sign_pref),
        'sign_display': sign_display,
        'sign_flip_applied': sign_flip_applied,
        'regulatory_max': regulatory_max,
        'regulatory_min': regulatory_min,
        'display_max': display_max,
        'display_min': display_min,
        'display_mode': str(display_mode or 'cluster'),
        'filter_meta': dict(filter_meta or {}),
    }
