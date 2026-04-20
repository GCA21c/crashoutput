import numpy as np

from app.core.dummy import get_neck_dummy_profile
from app.services.preprocessing.cfc_filter import apply_cfc_filter_to_series


def compute_neck_nij_metrics(time_s, fz_n, my_nm, apply_cfc600=True, criterion_key="H3_50%M", fz_unit=None, my_unit=None, fx_n=None, fx_unit=None, moment_is_mocy=False, fz_peak_n=None):
    """Compute Nij from upper neck Fz and MOCy.

    According to the crash criteria reference, Nij uses upper-neck Force Z
    filtered at CFC 600 together with the total moment about the occipital
    condyle (MOCy). For upper load cells this is derived from the filtered raw
    My and Fx channels using the dummy/load-cell lever arm D:

        MOCy = My - Fx * D

    If Fx is not available, the function falls back to raw My and reports that
    MOC correction was not applied.
    """
    time_arr = np.asarray(time_s, dtype=float)
    fz = np.asarray(fz_n, dtype=float)
    my = np.asarray(my_nm, dtype=float)
    fx = None if fx_n is None else np.asarray(fx_n, dtype=float)

    fz_unit_text = str(fz_unit or '').strip()
    my_unit_text = str(my_unit or '').strip()
    fx_unit_text = str(fx_unit or '').strip()

    # Normalize common engineering units to the convention used by Nij:
    # axial force in N and bending moment in Nm.
    fz_unit_l = fz_unit_text.lower().replace('·', '').replace('*', '').replace(' ', '')
    my_unit_l = my_unit_text.lower().replace('·', '').replace('*', '').replace(' ', '')

    if fz_unit_l in ('kn', 'kilonewton', 'kilonewtons'):
        fz = fz * 1000.0
        fz_unit_text = 'N'
    elif fz_unit_l in ('mn',):
        fz = fz * 1_000_000.0
        fz_unit_text = 'N'

    if my_unit_l in ('nmm', 'nmm.', 'n-mm', 'n/mm', 'newtonmillimeter', 'newtonmillimeters'):
        my = my / 1000.0
        my_unit_text = 'Nm'
    elif my_unit_l in ('knm', 'k nm', 'kn-m', 'kilonewtonmeter', 'kilonewtonmeters'):
        my = my * 1000.0
        my_unit_text = 'Nm'

    if fx is not None:
        fx_unit_l = fx_unit_text.lower().replace('·', '').replace('*', '').replace(' ', '')
        if fx_unit_l in ('kn', 'kilonewton', 'kilonewtons'):
            fx = fx * 1000.0
            fx_unit_text = 'N'
        elif fx_unit_l in ('mn',):
            fx = fx * 1_000_000.0
            fx_unit_text = 'N'

    preset_key = str(criterion_key or "H3_50%M")
    limits = get_neck_dummy_profile(preset_key)

    if apply_cfc600:
        fz = apply_cfc_filter_to_series(time_arr, fz, 600)
        my = apply_cfc_filter_to_series(time_arr, my, 600)
        if fx is not None:
            fx = apply_cfc_filter_to_series(time_arr, fx, 600)

    peak_force = np.asarray(fz_peak_n if fz_peak_n is not None else fz, dtype=float)

    moc_d = float(limits.get('moc_d', 0.0) or 0.0)
    resolved_load_cell_type = 'Preset D'
    my_source = my.copy()
    if moment_is_mocy:
        moc_applied = True
    else:
        moc_applied = fx is not None and np.isfinite(fx).any() and abs(moc_d) > 0.0
        if moc_applied:
            my = my - fx * moc_d

    # Nij case calculation needs both Fz and MOCy to be valid at the same sample.
    # However peak Fz / peak My summaries are properties of the individual
    # input channels, so they must not be restricted by the joint-valid mask used for Nij.
    valid = np.isfinite(time_arr) & np.isfinite(fz) & np.isfinite(my)
    if not np.any(valid):
        return None

    valid_idx = np.flatnonzero(valid)
    tv = time_arr[valid]
    fzv = fz[valid]
    myv = my[valid]

    force_valid = np.isfinite(time_arr) & np.isfinite(peak_force)
    moment_valid = np.isfinite(time_arr) & np.isfinite(my)
    fv_t = time_arr[force_valid]
    fv_fz = peak_force[force_valid]
    mv_t = time_arr[moment_valid]
    mv_my = my[moment_valid]

    ntf = np.full_like(fz, np.nan, dtype=float)
    nte = np.full_like(fz, np.nan, dtype=float)
    ncf = np.full_like(fz, np.nan, dtype=float)
    nce = np.full_like(fz, np.nan, dtype=float)
    nij = np.full_like(fz, np.nan, dtype=float)

    tf_mask_v = (fzv > 0.0) & (myv > 0.0)
    te_mask_v = (fzv > 0.0) & (myv < 0.0)
    cf_mask_v = (fzv < 0.0) & (myv > 0.0)
    ce_mask_v = (fzv < 0.0) & (myv < 0.0)

    # The NIJ case rule uses an AND condition for each case.
    # If the force/moment sign pair does not match a case, that case is zero.
    # For compression and extension, the critical values are negative in the
    # published convention so that Fz/Fzc and My/MyE still produce positive Nij.
    fzt = float(limits['Fzt'])
    fzc = -abs(float(limits['Fzc']))
    myf = float(limits['MyF'])
    mye = -abs(float(limits['MyE']))

    ntf_v = np.zeros_like(fzv, dtype=float)
    nte_v = np.zeros_like(fzv, dtype=float)
    ncf_v = np.zeros_like(fzv, dtype=float)
    nce_v = np.zeros_like(fzv, dtype=float)
    nij_v = np.zeros_like(fzv, dtype=float)
    mode_v = np.full(fzv.shape, '', dtype=object)

    if np.any(tf_mask_v):
        val = (fzv[tf_mask_v] / fzt) + (myv[tf_mask_v] / myf)
        ntf_v[tf_mask_v] = val
        nij_v[tf_mask_v] = val
        mode_v[tf_mask_v] = 'NTF'
    if np.any(te_mask_v):
        val = (fzv[te_mask_v] / fzt) + (myv[te_mask_v] / mye)
        nte_v[te_mask_v] = val
        nij_v[te_mask_v] = val
        mode_v[te_mask_v] = 'NTE'
    if np.any(cf_mask_v):
        val = (fzv[cf_mask_v] / fzc) + (myv[cf_mask_v] / myf)
        ncf_v[cf_mask_v] = val
        nij_v[cf_mask_v] = val
        mode_v[cf_mask_v] = 'NCF'
    if np.any(ce_mask_v):
        val = (fzv[ce_mask_v] / fzc) + (myv[ce_mask_v] / mye)
        nce_v[ce_mask_v] = val
        nij_v[ce_mask_v] = val
        mode_v[ce_mask_v] = 'NCE'

    ntf[valid] = ntf_v
    nte[valid] = nte_v
    ncf[valid] = ncf_v
    nce[valid] = nce_v
    nij[valid] = nij_v

    case_label_full = np.full(time_arr.shape, '', dtype=object)
    case_label_full[valid] = mode_v

    def _global_extreme_idx(arr, mode='max'):
        arr = np.asarray(arr, dtype=float)
        finite = np.isfinite(arr)
        if not np.any(finite):
            return None
        finite_idx = np.flatnonzero(finite)
        arr_f = arr[finite]
        target = np.nanmax(arr_f) if mode == 'max' else np.nanmin(arr_f)
        cand = np.flatnonzero(np.isclose(arr_f, target, rtol=1e-12, atol=1e-12))
        return int(finite_idx[cand[-1]]) if cand.size else int(finite_idx[-1])

    def _global_peak_value(arr, mode='max'):
        idx = _global_extreme_idx(arr, mode)
        return None if idx is None else float(np.asarray(arr, dtype=float)[idx])

    peak_tension_idx = _global_extreme_idx(fv_fz, 'max')
    peak_compression_idx = _global_extreme_idx(fv_fz, 'min')
    peak_flexion_idx = _global_extreme_idx(mv_my, 'max')
    peak_extension_idx = _global_extreme_idx(mv_my, 'min')
    peak_tension_val = _global_peak_value(fv_fz, 'max')
    peak_compression_val = _global_peak_value(fv_fz, 'min')
    peak_flexion_val = _global_peak_value(mv_my, 'max')
    peak_extension_val = _global_peak_value(mv_my, 'min')

    peak_ntf_idx = _global_extreme_idx(ntf_v, 'max')
    peak_nte_idx = _global_extreme_idx(nte_v, 'max')
    peak_ncf_idx = _global_extreme_idx(ncf_v, 'max')
    peak_nce_idx = _global_extreme_idx(nce_v, 'max')
    peak_overall_idx = _global_extreme_idx(nij_v, 'max')
    peak_overall = _global_peak_value(nij_v, 'max')
    dominant_mode = mode_v[peak_overall_idx] if peak_overall_idx is not None and mode_v.size else '-'

    joint_peak_tension_idx = _global_extreme_idx(fzv, 'max')
    joint_peak_compression_idx = _global_extreme_idx(fzv, 'min')
    joint_peak_tension_val = _global_peak_value(fzv, 'max')
    joint_peak_compression_val = _global_peak_value(fzv, 'min')

    metrics = {
        'time': time_arr,
        'valid_index': valid_idx,
        'fz_filtered': peak_force,
        'fz_peak_filtered': peak_force,
        'fz_nij_filtered': fz,
        'my_raw_filtered': my_source,
        'my_filtered': my,
        'fx_filtered': fx if fx is not None else None,
        'ntf': ntf,
        'nte': nte,
        'ncf': ncf,
        'nce': nce,
        'nij': nij,
        'case_label': case_label_full,
        'peak_tension_fz': peak_tension_val,
        'peak_compression_fz_raw': peak_compression_val,
        'peak_compression_fz': peak_compression_val,
        'joint_peak_tension_fz': joint_peak_tension_val,
        'joint_peak_compression_fz_raw': joint_peak_compression_val,
        'joint_peak_compression_fz': joint_peak_compression_val,
        'peak_flexion_my': peak_flexion_val,
        'peak_extension_my': peak_extension_val,
        'peak_tension_idx_force_valid': peak_tension_idx,
        'peak_compression_idx_force_valid': peak_compression_idx,
        'peak_flexion_idx_moment_valid': peak_flexion_idx,
        'peak_extension_idx_moment_valid': peak_extension_idx,
        'peak_tension_idx': int(np.flatnonzero(force_valid)[peak_tension_idx]) if peak_tension_idx is not None else None,
        'peak_compression_idx': int(np.flatnonzero(force_valid)[peak_compression_idx]) if peak_compression_idx is not None else None,
        'joint_peak_tension_idx': int(valid_idx[joint_peak_tension_idx]) if joint_peak_tension_idx is not None else None,
        'joint_peak_compression_idx': int(valid_idx[joint_peak_compression_idx]) if joint_peak_compression_idx is not None else None,
        'peak_flexion_idx': int(np.flatnonzero(moment_valid)[peak_flexion_idx]) if peak_flexion_idx is not None else None,
        'peak_extension_idx': int(np.flatnonzero(moment_valid)[peak_extension_idx]) if peak_extension_idx is not None else None,
        'peak_tension_time': float(fv_t[peak_tension_idx]) if peak_tension_idx is not None else None,
        'peak_compression_time': float(fv_t[peak_compression_idx]) if peak_compression_idx is not None else None,
        'joint_peak_tension_time': float(tv[joint_peak_tension_idx]) if joint_peak_tension_idx is not None else None,
        'joint_peak_compression_time': float(tv[joint_peak_compression_idx]) if joint_peak_compression_idx is not None else None,
        'peak_flexion_time': float(mv_t[peak_flexion_idx]) if peak_flexion_idx is not None else None,
        'peak_extension_time': float(mv_t[peak_extension_idx]) if peak_extension_idx is not None else None,
        'peak_ntf': _global_peak_value(ntf_v, 'max'),
        'peak_nte': _global_peak_value(nte_v, 'max'),
        'peak_ncf': _global_peak_value(ncf_v, 'max'),
        'peak_nce': _global_peak_value(nce_v, 'max'),
        'peak_ntf_idx_valid': peak_ntf_idx,
        'peak_nte_idx_valid': peak_nte_idx,
        'peak_ncf_idx_valid': peak_ncf_idx,
        'peak_nce_idx_valid': peak_nce_idx,
        'peak_ntf_time': float(tv[peak_ntf_idx]) if peak_ntf_idx is not None else None,
        'peak_nte_time': float(tv[peak_nte_idx]) if peak_nte_idx is not None else None,
        'peak_ncf_time': float(tv[peak_ncf_idx]) if peak_ncf_idx is not None else None,
        'peak_nce_time': float(tv[peak_nce_idx]) if peak_nce_idx is not None else None,
        'overall_nij': peak_overall,
        'overall_nij_idx_valid': peak_overall_idx,
        'overall_nij_idx': int(valid_idx[peak_overall_idx]) if peak_overall_idx is not None else None,
        'overall_nij_time': float(tv[peak_overall_idx]) if peak_overall_idx is not None else None,
        'dominant_mode': dominant_mode,
        'criteria': {
            'criterion_key': preset_key,
            'criterion_label': limits.get('label', preset_key),
            'dummy_family': limits.get('dummy_family', '-'),
            'source': limits.get('source', '-'),
            'input_force': 'Fz',
            'input_moment': 'MOCy' if (moc_applied or moment_is_mocy) else 'My',
            'f_tension_crit': limits['Fzt'],
            'f_compression_crit': -abs(limits['Fzc']),
            'm_flexion_crit': limits['MyF'],
            'm_extension_crit': -abs(limits['MyE']),
            'filter': 'CFC 600' if apply_cfc600 else 'Raw',
            'peak_tension_limit': limits.get('peak_tension_limit'),
            'peak_compression_limit': limits.get('peak_compression_limit'),
            'peak_rule': 'global extrema on individual source channel validity (Fz or MOCy)',
            'input_force_unit': fz_unit_text or None,
            'input_moment_unit': my_unit_text or None,
            'input_fx_unit': fx_unit_text or None,
            'moc_d': moc_d,
            'moc_applied': moc_applied,
            'moment_is_mocy': bool(moment_is_mocy),
            'load_cell_type': resolved_load_cell_type,
        }
    }
    return metrics
