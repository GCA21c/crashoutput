"""CHEST dummy profile presets backed by the central dummy engine."""
from .engine import get_available_dummy_profile_names, get_dummy_module_factors

CHEST_DUMMY_PROFILES = {name: get_dummy_module_factors(name, 'chest') for name in get_available_dummy_profile_names('chest', 'FRONTAL')}

def get_chest_dummy_profile(profile_key):
    key = str(profile_key or 'H3_50%M')
    profile = get_dummy_module_factors(key, 'chest', 'FRONTAL')
    if not profile:
        profile = get_dummy_module_factors('H3_50%M', 'chest', 'FRONTAL')
    return dict(profile)
