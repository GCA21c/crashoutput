import numpy as np


def convert_accel_to_g_series(values, unit_text=''):
    arr = np.asarray(values, dtype=float)
    unit = str(unit_text or '').lower().replace(' ', '')
    if 'm/s' in unit or 'ms-2' in unit or 'mps2' in unit:
        return arr / 9.80665
    return arr


def convert_disp_to_mm_series(values, unit_text=''):
    arr = np.asarray(values, dtype=float)
    unit = str(unit_text or '').lower().replace(' ', '')
    if unit in ('m', 'meter', 'meters'):
        return arr * 1000.0
    if unit in ('cm', 'centimeter', 'centimeters'):
        return arr * 10.0
    if unit in ('mm', 'millimeter', 'millimeters', ''):
        return arr
    if unit in ('in', 'inch', 'inches'):
        return arr * 25.4
    return arr


def pick_compression_positive(values_mm):
    arr = np.asarray(values_mm, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return 1.0
    vmax = np.nanmax(finite)
    vmin = np.nanmin(finite)
    return 1.0 if abs(vmax) >= abs(vmin) else -1.0
