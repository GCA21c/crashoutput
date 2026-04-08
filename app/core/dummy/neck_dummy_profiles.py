"""NECK dummy profile presets backed by the central dummy engine."""
from .engine import get_available_dummy_profile_names, get_dummy_module_factors

NECK_DUMMY_PROFILES = {name: get_dummy_module_factors(name, 'neck') for name in get_available_dummy_profile_names('neck', 'FRONTAL')}

def get_neck_dummy_profile(profile_key):
    key = str(profile_key or 'H3_50%M')
    profile = get_dummy_module_factors(key, 'neck', 'FRONTAL')
    if not profile:
        profile = get_dummy_module_factors('H3_50%M', 'neck', 'FRONTAL')
    return dict(profile)
