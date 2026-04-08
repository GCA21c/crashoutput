"""ILIAC dummy profile presets backed by the central dummy engine."""
from .engine import get_dummy_module_factors

ILIAC_DUMMY_PROFILES = {
    'Thor_50%M': dict(get_dummy_module_factors('Thor_50%M', 'iliac', 'FRONTAL')),
    'THOR_50M_ASIS': dict(get_dummy_module_factors('Thor_50%M', 'iliac', 'FRONTAL')),
    'THOR_AV_ASIS': dict(get_dummy_module_factors('Thor_50%M', 'iliac', 'FRONTAL')),
}


def get_iliac_dummy_profile(profile_key):
    key = str(profile_key or 'Thor_50%M')
    profile = get_dummy_module_factors(key, 'iliac', 'FRONTAL')
    if not profile:
        profile = get_dummy_module_factors('Thor_50%M', 'iliac', 'FRONTAL')
    profile.setdefault('label', 'THOR 50%M ASIS')
    return dict(profile)
