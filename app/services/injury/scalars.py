import numpy as np


def series_to_float(arr):
    values = np.asarray(arr, dtype=float)
    return values[np.isfinite(values)]


def convert_accel_to_g(values, unit_text=""):
    unit = str(unit_text or "").lower().replace(" ", "")
    vals = np.asarray(values, dtype=float)
    if "m/s" in unit or "ms-2" in unit or "mps2" in unit:
        return vals / 9.80665
    return vals
