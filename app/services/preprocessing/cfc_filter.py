import numpy as np
from scipy.signal import filtfilt

from app.services.preprocessing.timing import get_sample_rate


FILTER_EXTENSION_MODE = "End Points"

_CFC_SF = {
    60: 2.0775,
    180: 2.0775,
    600: 2.0775,
    1000: 2.0775,
}


def cfc_coefficients_sae_j211(fs, cfc_value):
    if fs is None or fs <= 0:
        return None
    sf = _CFC_SF.get(int(cfc_value), 2.0775)
    T = 1.0 / float(fs)
    wd = 2.0 * np.pi * float(cfc_value) * float(sf)
    wa = np.tan(wd * T / 2.0)
    den = 1.0 + np.sqrt(2.0) * wa + wa * wa
    if not np.isfinite(den) or den == 0.0:
        return None
    a0 = (wa * wa) / den
    a1 = 2.0 * a0
    a2 = a0
    b1 = -2.0 * ((wa * wa) - 1.0) / den
    b2 = (-1.0 + np.sqrt(2.0) * wa - wa * wa) / den
    # scipy.signal.filtfilt expects direct-form denominator [1, a1, a2] for
    # y[n] = b0*x[n] + ... - a1*y[n-1] - a2*y[n-2]. The SAE/J211 notation in
    # public examples is commonly rearranged as [1, -b1, -b2].
    b = np.asarray([a0, a1, a2], dtype=float)
    a = np.asarray([1.0, -b1, -b2], dtype=float)
    return b, a


def end_points_extend(y_segment, fs):
    """Extend a signal using constant end-point values before CFC filtering."""
    y = np.asarray(y_segment, dtype=float)
    if fs is None or fs <= 0 or y.size < 3:
        return y, 0

    ext_pts = max(1, int(np.ceil(0.010 * float(fs))))
    ext_pts = min(ext_pts, y.size - 1)
    if ext_pts <= 0:
        return y, 0

    pre = np.full(ext_pts, y[0], dtype=float)
    post = np.full(ext_pts, y[-1], dtype=float)
    extended = np.concatenate([pre, y, post])
    return extended, ext_pts


def apply_cfc_filter_segment(y_segment, fs, cfc_value):
    if fs is None or fs <= 0 or len(y_segment) < 8:
        return y_segment.copy()
    coeffs = cfc_coefficients_sae_j211(fs, cfc_value)
    if coeffs is None:
        return y_segment.copy()
    b, a = coeffs
    extended, ext_pts = end_points_extend(y_segment, fs)
    try:
        filtered = filtfilt(b, a, extended, method="pad", padtype=None, padlen=0)
        if ext_pts > 0:
            return filtered[ext_pts:ext_pts + len(y_segment)]
        return filtered[:len(y_segment)]
    except Exception:
        return y_segment.copy()


def apply_cfc_filter_to_series(time_arr, values, cfc_value):
    x_all = np.asarray(time_arr, dtype=float)
    y_all = np.asarray(values, dtype=float)
    out = y_all.copy()
    fs = get_sample_rate(x_all)
    valid = np.isfinite(x_all) & np.isfinite(y_all)
    if not np.any(valid):
        return out
    idx = np.flatnonzero(valid)
    split_points = np.where(np.diff(idx) > 1)[0] + 1
    groups = np.split(idx, split_points)
    for grp in groups:
        if grp.size < 8:
            continue
        out[grp] = apply_cfc_filter_segment(y_all[grp].astype(float), fs, cfc_value)
    return out
