import numpy as np

from app.services.preprocessing.filter_sources import parse_cfc_filter_label


def build_neck_injury_channels(metrics):
    """Build calculated neck injury channels for saving to _I datasets."""
    if not metrics:
        return {}

    def _same_cfc(label, cfc_value):
        parsed = parse_cfc_filter_label(label)
        return parsed == int(cfc_value)

    used_filters = dict((metrics or {}).get('used_filter_labels') or {})
    out = {}
    if metrics.get('fz_peak_filtered') is not None and not _same_cfc(used_filters.get('fz_peak'), 1000):
        out['NECKUP_FZ_CFC1000'] = np.asarray(metrics['fz_peak_filtered'], dtype=float)
    if metrics.get('fz_nij_filtered') is not None and not _same_cfc(used_filters.get('fz_nij'), 600):
        out['NECKUP_FZ_CFC600'] = np.asarray(metrics['fz_nij_filtered'], dtype=float)
    if metrics.get('fx_filtered') is not None and not _same_cfc(used_filters.get('fx_nij'), 600):
        out['NECKUP_FX_CFC600'] = np.asarray(metrics['fx_filtered'], dtype=float)
    if metrics.get('my_raw_filtered') is not None and not _same_cfc(used_filters.get('my_nij'), 600):
        out['NECKUP_MY_CFC600'] = np.asarray(metrics['my_raw_filtered'], dtype=float)
    if metrics.get('my_filtered') is not None:
        out['NECKUP_MOCY'] = np.asarray(metrics['my_filtered'], dtype=float)
    out['NECKUP_NIJ_TE'] = np.asarray(metrics.get('nte'), dtype=float)
    out['NECKUP_NIJ_TF'] = np.asarray(metrics.get('ntf'), dtype=float)
    out['NECKUP_NIJ_CE'] = np.asarray(metrics.get('nce'), dtype=float)
    out['NECKUP_NIJ_CF'] = np.asarray(metrics.get('ncf'), dtype=float)
    out['NECKUP_NIJ'] = np.asarray(metrics.get('nij'), dtype=float)
    return out


def build_neck_injury_channel_metadata(metrics):
    crit = dict((metrics or {}).get('criteria') or {})
    descriptions = {
        'NECKUP_FZ_CFC1000': 'Upper Neck Fz - CFC1000',
        'NECKUP_FZ_CFC600': 'Upper Neck Fz - CFC600',
        'NECKUP_FX_CFC600': 'Upper Neck Fx - CFC600',
        'NECKUP_MY_CFC600': 'Upper Neck My - CFC600',
        'NECKUP_MOCY': 'Occipital Condyle Moment - Y',
        'NECKUP_NIJ_TE': 'Upper Neck Nij - Tension Extension',
        'NECKUP_NIJ_TF': 'Upper Neck Nij - Tension Flexion',
        'NECKUP_NIJ_CE': 'Upper Neck Nij - Compression Extension',
        'NECKUP_NIJ_CF': 'Upper Neck Nij - Compression Flexion',
        'NECKUP_NIJ': 'Upper Neck Nij',
    }
    units = {
        'NECKUP_FZ_CFC1000': 'N',
        'NECKUP_FZ_CFC600': 'N',
        'NECKUP_FX_CFC600': 'N',
        'NECKUP_MY_CFC600': 'Nm',
        'NECKUP_MOCY': 'Nm',
        'NECKUP_NIJ_TE': 'Value',
        'NECKUP_NIJ_TF': 'Value',
        'NECKUP_NIJ_CE': 'Value',
        'NECKUP_NIJ_CF': 'Value',
        'NECKUP_NIJ': 'Value',
    }
    nij_filter = crit.get('filter', 'CFC 600') or 'CFC 600'
    filter_labels = {
        'NECKUP_FZ_CFC1000': 'CFC 1000',
        'NECKUP_FZ_CFC600': 'CFC 600',
        'NECKUP_FX_CFC600': 'CFC 600',
        'NECKUP_MY_CFC600': 'CFC 600',
        'NECKUP_MOCY': nij_filter,
        'NECKUP_NIJ_TE': nij_filter,
        'NECKUP_NIJ_TF': nij_filter,
        'NECKUP_NIJ_CE': nij_filter,
        'NECKUP_NIJ_CF': nij_filter,
        'NECKUP_NIJ': nij_filter,
    }
    return {'descriptions': descriptions, 'units': units, 'channel_filter_labels': filter_labels}
