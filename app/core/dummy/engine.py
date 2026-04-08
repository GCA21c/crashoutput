from __future__ import annotations

from copy import deepcopy

FRONTAL_UNIFIED_PROFILES = (
    'H3_50%M',
    'H3_5%F',
    'Q3_Child',
    'Q6_Child',
    'Q10_Child',
    'Thor_50%M',
    'H3_95%M',
)

SIDE_UNIFIED_PROFILES = (
    'WorldSID_50%M',
    'WorldSID_5%F',
    'ES2_50%M',
    'SIDIIs_5%F',
    'Thor_50%M_Side',
)

MODULE_DEFAULTS = {
    'head': 'H3_50%M',
    'neck': 'H3_50%M',
    'chest': 'H3_50%M',
    'pelvis': 'H3_50%M',
    'femur': 'H3_50%M',
    'knee': 'H3_50%M',
    'iliac': 'Thor_50%M',
    'tibia': 'H3_50%M',
}

_DUMMY_ENGINE = {
    'FRONTAL': {
        'H3_50%M': {
            'label': 'H3 50%M',
            'dummy_family': 'Hybrid III',
            'dummy_type_codes': ('H3',),
            'aliases': ('H3_50M_FMVSS208', 'H3_50M_EURO_NCAP'),
            'modules': {
                'head': {'source': 'FMVSS 208 / Euro NCAP frontal references', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'FMVSS 208 S6.6(a)', 'Fzt': 6806.0, 'Fzc': 6160.0, 'MyF': 310.0, 'MyE': 135.0, 'moc_d': 0.01778, 'peak_tension_limit': 4170.0, 'peak_compression_limit': 4000.0},
                'chest': {'source': 'FMVSS 208 S6.3/S6.4', 'accel_3ms_limit_g': 60.0, 'deflection_limit_mm': 76.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 229.0, 'scaling_factor': 1.3},
                'femur': {'source': 'FMVSS 208 S6.5', 'femur_force_limit_n': 2250.0 * 4.4482216152605, 'required_cfc': 600},
                'knee': {}, 'pelvis': {},
                'tibia': {'source': 'Euro NCAP frontal impact lower leg / IIHS lower leg review references', 'force_crit_n': 35900.0, 'moment_crit_nm': 225.0, 'ti_reference_line': 1.0, 'ti_secondary_line': 1.3, 'upper_ap_adjust_m_per_n': -0.02832, 'lower_ap_adjust_m_per_n': 0.006398},
            },
        },
        'H3_5%F': {
            'label': 'H3 5%F', 'dummy_family': 'Hybrid III', 'dummy_type_codes': ('HF',), 'aliases': ('HF_5F_FMVSS208', 'HF_5F_EURO_NCAP'),
            'modules': {
                'head': {'source': 'FMVSS 208 / Euro NCAP frontal references', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'FMVSS 208 S15.3.6(a)', 'Fzt': 4287.0, 'Fzc': 3880.0, 'MyF': 155.0, 'MyE': 67.0, 'moc_d': 0.01778, 'peak_tension_limit': 2620.0, 'peak_compression_limit': 2520.0},
                'chest': {'source': 'FMVSS 208 S15.3.3/S15.3.4', 'accel_3ms_limit_g': 60.0, 'deflection_limit_mm': 52.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 187.0, 'scaling_factor': 1.3},
                'femur': {'source': 'FMVSS 208 S15.3.5', 'femur_force_limit_n': 6805.0, 'required_cfc': 600},
                'knee': {}, 'pelvis': {},
                'tibia': {'source': 'Euro NCAP frontal impact lower leg / IIHS lower leg review references', 'force_crit_n': 35900.0, 'moment_crit_nm': 225.0, 'ti_reference_line': 1.0, 'ti_secondary_line': 1.3, 'upper_ap_adjust_m_per_n': -0.02832, 'lower_ap_adjust_m_per_n': 0.006398},
            },
        },
        'Q3_Child': {
            'label': 'Q3 Child', 'dummy_family': 'Child', 'dummy_type_codes': ('Q3', 'Y6'), 'aliases': ('Y6_3YO_FMVSS208',),
            'modules': {
                'head': {'source': 'FMVSS 208 child frontal references', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'FMVSS 208 S21.5.5(a)', 'Fzt': 2120.0, 'Fzc': 2120.0, 'MyF': 68.0, 'MyE': 27.0, 'moc_d': 0.0, 'peak_tension_limit': 1130.0, 'peak_compression_limit': 1380.0},
                'chest': {'source': 'FMVSS 208 S21.5.3/S21.5.4', 'accel_3ms_limit_g': 55.0, 'deflection_limit_mm': 34.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 122.0, 'scaling_factor': 1.3},
                'femur': {}, 'knee': {}, 'pelvis': {}, 'tibia': {},
            },
        },
        'Q6_Child': {
            'label': 'Q6 Child', 'dummy_family': 'Child', 'dummy_type_codes': ('Q6', 'Y7'), 'aliases': ('Y7_6YO_FMVSS208',),
            'modules': {
                'head': {'source': 'FMVSS 208 child frontal references', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'FMVSS 208 S23.5.5(a)', 'Fzt': 2800.0, 'Fzc': 2800.0, 'MyF': 93.0, 'MyE': 37.0, 'moc_d': 0.01778, 'peak_tension_limit': 1490.0, 'peak_compression_limit': 1820.0},
                'chest': {'source': 'FMVSS 208 S23.5.3/S23.5.4', 'accel_3ms_limit_g': 60.0, 'deflection_limit_mm': 40.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 143.0, 'scaling_factor': 1.3},
                'femur': {}, 'knee': {}, 'pelvis': {}, 'tibia': {},
            },
        },
        'Q10_Child': {
            'label': 'Q10 Child', 'dummy_family': 'Child', 'dummy_type_codes': ('QA', 'Y8', 'Y10'), 'aliases': ('Y10_10YO_FMVSS208', 'Y8_LEGACY_VBS'),
            'modules': {
                'head': {'source': 'Frontal child head reference', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'Legacy VBS 10-year-old reference', 'Fzt': 3380.0, 'Fzc': 3380.0, 'MyF': 126.0, 'MyE': 50.0, 'moc_d': 0.01778, 'peak_tension_limit': None, 'peak_compression_limit': None},
                'chest': {'source': '10YO frontal chest reference', 'accel_3ms_limit_g': 60.0, 'deflection_limit_mm': 52.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 166.0, 'scaling_factor': 1.3},
                'femur': {}, 'knee': {}, 'pelvis': {}, 'tibia': {},
            },
        },
        'Thor_50%M': {
            'label': 'THOR 50%M', 'dummy_family': 'THOR', 'dummy_type_codes': ('TH',), 'aliases': ('TH_LEGACY_VBS',),
            'modules': {
                'head': {'source': 'Frontal THOR head reference', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'Legacy THOR neck reference', 'Fzt': 2520.0, 'Fzc': 3640.0, 'MyF': 48.0, 'MyE': 72.0, 'moc_d': 0.0, 'peak_tension_limit': None, 'peak_compression_limit': None},
                'chest': {'source': 'Temporary fallback to adult frontal VC constants', 'accel_3ms_limit_g': 60.0, 'deflection_limit_mm': 76.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 229.0, 'scaling_factor': 1.3},
                'femur': {}, 'knee': {}, 'pelvis': {}, 'tibia': {},
                'iliac': {'source': 'THOR ASIS reference', 'iliac_force_limit_n': None, 'iliac_moment_limit_nm': None},
            },
        },
        'H3_95%M': {
            'label': 'H3 95%M', 'dummy_family': 'Hybrid III', 'dummy_type_codes': ('HM',), 'aliases': ('HM_LEGACY_VBS', 'H3_95M_FMVSS208', 'H3_95M_EURO_NCAP'),
            'modules': {
                'head': {'source': 'FMVSS 208 / Euro NCAP frontal references', 'hic15_limit': 700.0, 'hic36_limit': 1000.0, 'head_3ms_limit_g': 80.0, 'required_cfc': 1000},
                'neck': {'source': 'Legacy VBS 95th male reference', 'Fzt': 8216.0, 'Fzc': 7440.0, 'MyF': 415.0, 'MyE': 179.0, 'moc_d': 0.01778, 'peak_tension_limit': None, 'peak_compression_limit': None},
                'chest': {'source': 'VC dummy constant/scaling reference', 'accel_3ms_limit_g': 60.0, 'deflection_limit_mm': 76.0, 'vc_limit_mps': 1.0, 'dummy_constant_mm': 254.0, 'scaling_factor': 1.3},
                'femur': {'source': 'FMVSS 208 adult upper-leg force reference', 'femur_force_limit_n': 2250.0 * 4.4482216152605, 'required_cfc': 600},
                'knee': {}, 'pelvis': {},
                'tibia': {'source': 'Euro NCAP frontal impact lower leg / IIHS lower leg review references', 'force_crit_n': 35900.0, 'moment_crit_nm': 225.0, 'ti_reference_line': 1.0, 'ti_secondary_line': 1.3, 'upper_ap_adjust_m_per_n': -0.02832, 'lower_ap_adjust_m_per_n': 0.006398},
            },
        },
    },
    'SIDE': {
        'WorldSID_50%M': {'label': 'WorldSID 50%M', 'dummy_family': 'WorldSID', 'dummy_type_codes': ('WS',), 'aliases': (), 'modules': {}},
        'WorldSID_5%F': {'label': 'WorldSID 5%F', 'dummy_family': 'WorldSID', 'dummy_type_codes': ('WF',), 'aliases': (), 'modules': {}},
        'ES2_50%M': {'label': 'ES-2 50%M', 'dummy_family': 'ES-2', 'dummy_type_codes': ('E2', 'ES'), 'aliases': (), 'modules': {}},
        'SIDIIs_5%F': {'label': 'SID-IIs 5%F', 'dummy_family': 'SID-IIs', 'dummy_type_codes': ('SI',), 'aliases': (), 'modules': {}},
        'Thor_50%M_Side': {'label': 'THOR 50%M Side', 'dummy_family': 'THOR', 'dummy_type_codes': ('TH',), 'aliases': (), 'modules': {}},
    },
}

_ALIAS_TO_UNIFIED = {}
_CODE_TO_UNIFIED_BY_MODE = {}
for mode, profiles in _DUMMY_ENGINE.items():
    _CODE_TO_UNIFIED_BY_MODE[mode] = {}
    for unified_name, payload in profiles.items():
        _ALIAS_TO_UNIFIED[unified_name.upper()] = (mode, unified_name)
        for alias in payload.get('aliases', ()): _ALIAS_TO_UNIFIED[str(alias).upper()] = (mode, unified_name)
        for code in payload.get('dummy_type_codes', ()): _CODE_TO_UNIFIED_BY_MODE[mode][str(code).upper()] = unified_name


def _normalize_mode(test_mode: str | None) -> str:
    text = str(test_mode or 'FRONTAL').strip().upper()
    return text if text in _DUMMY_ENGINE else 'FRONTAL'


def resolve_dummy_profile_key(profile_name: str | None, test_mode: str | None = None, module: str | None = None) -> tuple[str, str]:
    mode = _normalize_mode(test_mode)
    raw = str(profile_name or '').strip()
    if not raw:
        return mode, MODULE_DEFAULTS.get(str(module or '').strip().lower(), FRONTAL_UNIFIED_PROFILES[0])
    lookup = _ALIAS_TO_UNIFIED.get(raw.upper())
    if lookup:
        lookup_mode, unified_name = lookup
        if test_mode:
            return _normalize_mode(test_mode), unified_name
        return lookup_mode, unified_name
    return mode, raw


def get_dummy_profile_catalog(test_mode: str | None = 'FRONTAL') -> dict:
    return deepcopy(_DUMMY_ENGINE.get(_normalize_mode(test_mode), {}))


def get_available_dummy_profile_names(module: str | None = None, test_mode: str | None = 'FRONTAL') -> tuple[str, ...]:
    mode = _normalize_mode(test_mode)
    profiles = _DUMMY_ENGINE.get(mode, {})
    module_key = str(module or '').strip().lower()
    result = []
    for name, payload in profiles.items():
        modules = payload.get('modules', {})
        if not module_key or module_key in modules or mode == 'FRONTAL':
            result.append(name)
    return tuple(result)


def get_dummy_profile(profile_name: str | None, test_mode: str | None = 'FRONTAL') -> dict:
    mode, unified_name = resolve_dummy_profile_key(profile_name, test_mode=test_mode)
    payload = deepcopy((_DUMMY_ENGINE.get(mode, {}) or {}).get(unified_name) or {})
    payload['profile_name'] = unified_name
    payload['test_mode'] = mode
    return payload


def get_dummy_module_factors(profile_name: str | None, module: str, test_mode: str | None = 'FRONTAL') -> dict:
    module_key = str(module or '').strip().lower()
    mode, unified_name = resolve_dummy_profile_key(profile_name, test_mode=test_mode, module=module_key)
    payload = deepcopy((_DUMMY_ENGINE.get(mode, {}) or {}).get(unified_name) or {})
    factors = deepcopy((payload.get('modules') or {}).get(module_key) or {})
    if factors:
        factors.setdefault('label', payload.get('label') or unified_name)
        factors.setdefault('criterion_profile_name', unified_name)
        factors.setdefault('test_mode', mode)
        return factors
    default_name = MODULE_DEFAULTS.get(module_key)
    if default_name and default_name != unified_name:
        fallback_payload = deepcopy((_DUMMY_ENGINE.get(mode, {}) or {}).get(default_name) or (_DUMMY_ENGINE['FRONTAL'].get(default_name) or {}))
        factors = deepcopy((fallback_payload.get('modules') or {}).get(module_key) or {})
        if factors:
            factors.setdefault('fallback_from', unified_name)
            factors.setdefault('label', fallback_payload.get('label') or default_name)
            factors.setdefault('criterion_profile_name', default_name)
            factors.setdefault('test_mode', mode)
    return factors


def infer_dummy_profile_from_codes(dummy_type_code: str | None, test_mode: str | None = 'FRONTAL', module: str | None = None) -> str:
    mode = _normalize_mode(test_mode)
    code = str(dummy_type_code or '').strip().upper()
    if not code:
        return MODULE_DEFAULTS.get(str(module or '').strip().lower(), FRONTAL_UNIFIED_PROFILES[0])
    mapped = (_CODE_TO_UNIFIED_BY_MODE.get(mode) or {}).get(code)
    if mapped:
        return mapped
    return MODULE_DEFAULTS.get(str(module or '').strip().lower(), FRONTAL_UNIFIED_PROFILES[0])
