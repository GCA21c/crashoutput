"""FEMUR dummy profile presets backed by the central dummy engine."""
from .engine import get_available_dummy_profile_names, get_dummy_module_factors

FEMUR_DUMMY_PROFILES = {name: get_dummy_module_factors(name, 'femur') for name in get_available_dummy_profile_names('femur', 'FRONTAL')}

def get_femur_dummy_profile(profile_key):
    key = str(profile_key or 'H3_50%M')
    profile = get_dummy_module_factors(key, 'femur', 'FRONTAL')
    if not profile:
        profile = get_dummy_module_factors('H3_50%M', 'femur', 'FRONTAL')
    return dict(profile)
