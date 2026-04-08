"""TIBIA dummy profile presets backed by the central dummy engine."""
from .engine import get_available_dummy_profile_names, get_dummy_module_factors

TIBIA_DUMMY_PROFILES = {name: get_dummy_module_factors(name, 'tibia') for name in get_available_dummy_profile_names('tibia', 'FRONTAL')}

def get_tibia_dummy_profile(profile_key):
    key = str(profile_key or 'H3_50%M')
    profile = get_dummy_module_factors(key, 'tibia', 'FRONTAL')
    if not profile:
        profile = get_dummy_module_factors('H3_50%M', 'tibia', 'FRONTAL')
    return dict(profile)
