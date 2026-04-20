import numpy as np


def cumtrapz(y, x):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(y, dtype=float)
    if y.size <= 1:
        return out
    out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return out


def prepare_hic_series(time_s, accel_g):
    t = np.asarray(time_s, dtype=float)
    a = np.asarray(accel_g, dtype=float)
    valid = np.isfinite(t) & np.isfinite(a)
    t = t[valid]
    a = a[valid]
    if t.size < 3:
        return None, None

    order = np.argsort(t, kind='mergesort')
    t = t[order]
    a = a[order]

    keep = np.ones(t.size, dtype=bool)
    keep[1:] = np.diff(t) > 0.0
    t = t[keep]
    a = a[keep]
    if t.size < 3:
        return None, None
    return t, a


def integral_at_query(query_t, t, a, integ):
    q = float(query_t)
    if q <= float(t[0]):
        return 0.0
    if q >= float(t[-1]):
        return float(integ[-1])

    idx = int(np.searchsorted(t, q, side='right') - 1)
    if idx < 0:
        return 0.0
    if idx >= len(t) - 1:
        return float(integ[-1])

    t0 = float(t[idx])
    t1 = float(t[idx + 1])
    a0 = float(a[idx])
    a1 = float(a[idx + 1])
    dt = t1 - t0
    if dt <= 0.0:
        return float(integ[idx])

    dq = q - t0
    slope = (a1 - a0) / dt
    aq = a0 + slope * dq
    partial = 0.5 * (a0 + aq) * dq
    return float(integ[idx] + partial)


def value_at_query(query_t, t, a):
    q = float(query_t)
    if q <= float(t[0]):
        return float(a[0])
    if q >= float(t[-1]):
        return float(a[-1])
    return float(np.interp(q, t, a))


def update_best_hic(best_info, start_time, end_time, area, full_time, full_signal):
    dt = float(end_time - start_time)
    if dt <= 0.0:
        return best_info
    mean_a = float(area / dt)
    hic = float(dt * (abs(mean_a) ** 2.5))
    if (best_info is None) or (hic > best_info['value'] + 1e-15):
        return {
            'value': hic,
            'start_time': float(start_time),
            'end_time': float(end_time),
            'duration': dt,
            'mean_accel_g': mean_a,
            'time': full_time.copy(),
            'signal': full_signal.copy(),
        }
    return best_info


def compute_hic_details(time_s, accel_g, max_window_s=0.036):
    t, a = prepare_hic_series(time_s, accel_g)
    if t is None:
        return None

    integ = cumtrapz(a, t)
    n = t.size
    window = float(max_window_s)
    best_info = None

    j = 1
    for i in range(n - 1):
        if j < i + 1:
            j = i + 1
        while j < n and (t[j] - t[i]) <= window + 1e-15:
            j += 1
        end_limit = j - 1
        for k in range(i + 1, end_limit + 1):
            area = float(integ[k] - integ[i])
            best_info = update_best_hic(best_info, t[i], t[k], area, t, a)

    for i in range(n - 1):
        end_t = float(t[i] + window)
        if end_t > float(t[-1]) + 1e-15:
            break
        area = integral_at_query(end_t, t, a, integ) - float(integ[i])
        best_info = update_best_hic(best_info, t[i], end_t, area, t, a)

    for j in range(1, n):
        start_t = float(t[j] - window)
        if start_t < float(t[0]) - 1e-15:
            continue
        area = float(integ[j]) - integral_at_query(start_t, t, a, integ)
        best_info = update_best_hic(best_info, start_t, t[j], area, t, a)

    if best_info is None:
        return None

    start_y = value_at_query(best_info['start_time'], t, a)
    end_y = value_at_query(best_info['end_time'], t, a)
    best_info['interval_signal'] = {
        'start_value': start_y,
        'end_value': end_y,
    }
    return best_info


def level_exceedance_intervals(time_s, signal, level):
    t, y = prepare_hic_series(time_s, signal)
    if t is None:
        return [], None, None
    lvl = float(level)
    intervals = []
    in_interval = bool(y[0] > lvl)
    start_t = float(t[0]) if in_interval else None
    for i in range(len(t) - 1):
        t0 = float(t[i])
        t1 = float(t[i + 1])
        y0 = float(y[i])
        y1 = float(y[i + 1])
        above0 = y0 > lvl
        above1 = y1 > lvl
        if above0 == above1:
            continue
        if np.isclose(y1, y0, rtol=0.0, atol=1e-15):
            cross_t = t1
        else:
            cross_t = t0 + (lvl - y0) * (t1 - t0) / (y1 - y0)
        cross_t = float(min(max(cross_t, t0), t1))
        if above0 and not above1:
            if in_interval and start_t is not None:
                intervals.append((float(start_t), cross_t))
            in_interval = False
            start_t = None
        elif (not above0) and above1:
            start_t = cross_t
            in_interval = True
    if in_interval and start_t is not None:
        intervals.append((float(start_t), float(t[-1])))
    return intervals, t, y


def clip_exceedance_detail(time_s, signal, window_s=0.003, mode='single', use_abs=True):
    arr = np.asarray(signal, dtype=float)
    arr_eval = np.abs(arr) if use_abs else arr
    intervals0, t, y = level_exceedance_intervals(time_s, arr_eval, 0.0)
    if t is None or y is None or t.size < 2:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }
    total_span = float(t[-1] - t[0])
    if total_span <= 0.0:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }

    req = float(window_s)

    def predicate(level):
        intervals, _, _ = level_exceedance_intervals(t, y, level)
        if not intervals:
            return False, intervals
        if mode == 'single':
            ok = any((b - a) >= req - 1e-15 for a, b in intervals)
        else:
            ok = sum((b - a) for a, b in intervals) >= req - 1e-15
        return ok, intervals

    lo = 0.0
    hi = float(np.nanmax(y[np.isfinite(y)])) if np.isfinite(y).any() else 0.0
    best_intervals = []
    ok0, ints0 = predicate(lo)
    if not ok0:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }
    best_intervals = ints0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        ok, intervals = predicate(mid)
        if ok:
            lo = mid
            best_intervals = intervals
        else:
            hi = mid
    value = float(lo)
    intervals, _, _ = level_exceedance_intervals(t, y, value)
    if not intervals:
        intervals = best_intervals
    if not intervals:
        return {
            'value': None,
            'time_s': None,
            'index': None,
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_value': None,
            'end_value': None,
            'mean_value': None,
            'method': f'3ms_exceedance_{mode}',
        }

    if mode == 'single':
        start_t, end_t = max(intervals, key=lambda ab: (ab[1] - ab[0], -ab[0]))
        duration_s = float(end_t - start_t)
    else:
        start_t = float(intervals[0][0])
        end_t = float(intervals[-1][1])
        duration_s = float(sum((b - a) for a, b in intervals))
    center_t = 0.5 * (start_t + end_t)
    idx = int(np.argmin(np.abs(t - center_t)))
    return {
        'value': value,
        'time_s': center_t,
        'index': idx,
        'start_time_s': start_t,
        'end_time_s': end_t,
        'duration_s': duration_s,
        'start_value': value_at_query(start_t, t, y),
        'end_value': value_at_query(end_t, t, y),
        'mean_value': None,
        'method': f'3ms_exceedance_{mode}',
    }


def compute_3ms_one_peak_exceedance_details(time_s, signal, use_abs=True, window_s=0.003):
    return clip_exceedance_detail(time_s, signal, window_s=window_s, mode='single', use_abs=use_abs)


def estimate_constant_dt(time_s):
    t = np.asarray(time_s, dtype=float)
    t = t[np.isfinite(t)]
    if t.size < 3:
        return None
    diffs = np.diff(t)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if diffs.size == 0:
        return None
    dt = float(np.median(diffs))
    if not np.isfinite(dt) or dt <= 0.0:
        return None
    tol = max(1e-12, dt * 0.02)
    if np.nanmax(np.abs(diffs - dt)) > tol:
        return None
    return dt


def compute_3ms_multiple_peak_exceedance_details(time_s, signal, use_abs=True, window_s=0.003, use_high_res_cumulative_3ms=True):
    t, y_src = prepare_hic_series(time_s, signal)
    empty = {
        'value': None,
        'time_s': None,
        'index': None,
        'start_time_s': None,
        'end_time_s': None,
        'duration_s': None,
        'start_value': None,
        'end_value': None,
        'mean_value': None,
        'method': '3ms_exceedance_multiple',
    }
    if t is None:
        return empty

    y = np.abs(y_src) if use_abs else y_src
    dt = estimate_constant_dt(t)
    req = float(window_s)
    if dt is None or req <= 0.0:
        return clip_exceedance_detail(time_s, signal, window_s=window_s, mode='multiple', use_abs=use_abs)

    samples_required = max(1, int(np.ceil((req - 1e-15) / dt)))
    if not bool(use_high_res_cumulative_3ms):
        samples_required += 1
    finite_vals = y[np.isfinite(y)]
    if finite_vals.size < samples_required:
        return empty

    sorted_vals = np.sort(finite_vals)[::-1]
    value = float(sorted_vals[samples_required - 1])

    eps = max(1e-12, abs(value) * 1e-12)
    intervals, t2, y2 = level_exceedance_intervals(t, y, value - eps)
    if not intervals:
        return clip_exceedance_detail(time_s, signal, window_s=window_s, mode='multiple', use_abs=use_abs)

    start_t = float(intervals[0][0])
    end_t = float(intervals[-1][1])
    duration_s = float(sum((b - a) for a, b in intervals))
    center_t = 0.5 * (start_t + end_t)
    idx = int(np.argmin(np.abs(t2 - center_t))) if t2.size else None
    return {
        'value': value,
        'time_s': center_t,
        'index': idx,
        'start_time_s': start_t,
        'end_time_s': end_t,
        'duration_s': duration_s,
        'start_value': value_at_query(start_t, t2, y2),
        'end_value': value_at_query(end_t, t2, y2),
        'mean_value': None,
        'method': '3ms_cumulative_sorted_constant_rate',
    }


def compute_hic(time_s, accel_g, max_window_s=0.036):
    info = compute_hic_details(time_s, accel_g, max_window_s=max_window_s)
    return None if info is None else float(info['value'])


def compute_3ms_clip_details(time_s, signal, use_abs=True, window_s=0.003):
    t, y_src = prepare_hic_series(time_s, signal)
    if t is None:
        return {
            "value": None,
            "time_s": None,
            "index": None,
            "start_time_s": None,
            "end_time_s": None,
            "duration_s": None,
            "start_value": None,
            "end_value": None,
            "mean_value": None,
            "method": "exact_3ms_window",
        }

    y = np.abs(y_src) if use_abs else y_src
    integ = cumtrapz(y, t)
    window = float(window_s)
    if t.size < 2 or window <= 0.0 or (float(t[-1]) - float(t[0])) < window - 1e-15:
        return {
            "value": None,
            "time_s": None,
            "index": None,
            "start_time_s": None,
            "end_time_s": None,
            "duration_s": None,
            "start_value": None,
            "end_value": None,
            "mean_value": None,
            "method": "exact_3ms_window",
        }

    best = None

    def _consider_window(start_t, end_t):
        nonlocal best
        dt = float(end_t - start_t)
        if dt <= 0.0:
            return
        area = integral_at_query(end_t, t, y, integ) - integral_at_query(start_t, t, y, integ)
        mean_v = float(area / dt)
        if (best is None) or (mean_v > best["value"] + 1e-15):
            center_t = 0.5 * (float(start_t) + float(end_t))
            idx = int(np.argmin(np.abs(t - center_t)))
            best = {
                "value": mean_v,
                "time_s": center_t,
                "index": idx,
                "start_time_s": float(start_t),
                "end_time_s": float(end_t),
                "duration_s": dt,
                "start_value": value_at_query(start_t, t, y),
                "end_value": value_at_query(end_t, t, y),
                "mean_value": mean_v,
                "method": "exact_3ms_window",
            }

    for i in range(len(t) - 1):
        start_t = float(t[i])
        end_t = start_t + window
        if end_t > float(t[-1]) + 1e-15:
            break
        _consider_window(start_t, end_t)

    for j in range(1, len(t)):
        end_t = float(t[j])
        start_t = end_t - window
        if start_t < float(t[0]) - 1e-15:
            continue
        _consider_window(start_t, end_t)

    if best is None:
        return {
            "value": None,
            "time_s": None,
            "index": None,
            "start_time_s": None,
            "end_time_s": None,
            "duration_s": None,
            "start_value": None,
            "end_value": None,
            "mean_value": None,
            "method": "exact_3ms_window",
        }
    return best


def compute_3ms_clip(time_s, signal):
    return compute_3ms_one_peak_exceedance_details(time_s, signal, use_abs=True).get("value")


def compute_3ms_one_peak_details(time_s, signal, use_abs=True):
    t = np.asarray(time_s, dtype=float)
    y_raw = np.asarray(signal, dtype=float)
    y = np.abs(y_raw) if use_abs else y_raw
    valid = np.isfinite(t) & np.isfinite(y)
    t = t[valid]
    y = y[valid]
    if t.size < 3:
        return {"value": None, "time_s": None, "index": None, "start_time_s": None, "end_time_s": None}

    def _strict_peaks(arr):
        if arr.size < 3:
            return np.array([], dtype=int)
        mid = arr[1:-1]
        return np.flatnonzero((mid > arr[:-2]) & (mid >= arr[2:])) + 1

    def _strict_valleys(arr):
        if arr.size < 3:
            return np.array([], dtype=int)
        mid = arr[1:-1]
        return np.flatnonzero((mid < arr[:-2]) & (mid <= arr[2:])) + 1

    peak_idx = _strict_peaks(y)
    if peak_idx.size == 0:
        return compute_3ms_clip_details(t, y_raw if not use_abs else y, use_abs=False)

    valley_idx = np.unique(np.concatenate(([0], _strict_valleys(y), [len(y) - 1]))).astype(int)
    best = None
    for pk in peak_idx:
        left_candidates = valley_idx[valley_idx < pk]
        right_candidates = valley_idx[valley_idx > pk]
        left = int(left_candidates[-1]) if left_candidates.size else 0
        right = int(right_candidates[0]) if right_candidates.size else (len(y) - 1)
        if right - left + 1 < 3:
            continue
        seg_t = t[left:right + 1]
        seg_y = y[left:right + 1]
        detail = compute_3ms_clip_details(seg_t, seg_y, use_abs=False)
        if detail.get('value') is None:
            continue
        if (best is None) or (float(detail['value']) > float(best['value']) + 1e-15):
            detail = dict(detail)
            if detail.get('index') is not None:
                detail['index'] = int(left + int(detail['index']))
            best = detail
    if best is not None:
        return best
    return compute_3ms_clip_details(t, y_raw if not use_abs else y, use_abs=False)
