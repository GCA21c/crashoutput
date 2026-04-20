import numpy as np


def compute_nij(fx_n, my_nm):
    nij_series = compute_nij_series(fx_n, my_nm)
    valid = nij_series[np.isfinite(nij_series)]
    return float(np.nanmax(valid)) if valid.size else None


def compute_nij_series(fx_n, my_nm):
    fx = np.asarray(fx_n, dtype=float)
    my = np.asarray(my_nm, dtype=float)
    valid = np.isfinite(fx) & np.isfinite(my)
    out = np.full_like(fx, np.nan, dtype=float)
    if not np.any(valid):
        return out
    fzc = 6160.0
    fzt = 6806.0
    myf = 310.0
    mye = 125.0
    fxv = fx[valid]
    myv = my[valid]
    f_term = np.where(fxv >= 0, fxv / fzt, (-fxv) / fzc)
    m_term = np.where(myv >= 0, myv / myf, (-myv) / mye)
    out[valid] = f_term + m_term
    return out
