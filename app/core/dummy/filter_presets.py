from __future__ import annotations

from copy import deepcopy

from .engine import resolve_dummy_profile_key


FILTER_PRESET_DB = {
    "FRONTAL": {
        "H3_50%M": {
            "label": "Hybrid III 50th Male frontal filtering preset",
            "rules": (
                {"body_region": "head", "measurement_family": "acceleration", "target_cfc": "CFC 1000"},
                {"body_region": "chest", "measurement_family": "acceleration", "target_cfc": "CFC 180"},
                {"body_region": "chest", "measurement_family": "deflection", "target_cfc": "CFC 180"},
                {"body_region": "pelvis", "measurement_family": "acceleration", "target_cfc": "CFC 180"},
                {"body_region": "neck", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "neck", "measurement_family": "moment", "target_cfc": "CFC 600"},
                {"body_region": "femur", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "tibia", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "tibia", "measurement_family": "moment", "target_cfc": "CFC 600"},
                {"body_region": "iliac", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "iliac", "measurement_family": "moment", "target_cfc": "CFC 600"},
                {"body_region": "knee", "measurement_family": "slider_displacement", "target_cfc": "CFC 180"},
            ),
        },
        "H3_5%F": {
            "label": "Hybrid III 5th Female frontal filtering preset",
            "rules": (
                {"body_region": "head", "measurement_family": "acceleration", "target_cfc": "CFC 1000"},
                {"body_region": "chest", "measurement_family": "acceleration", "target_cfc": "CFC 180"},
                {"body_region": "chest", "measurement_family": "deflection", "target_cfc": "CFC 180"},
                {"body_region": "pelvis", "measurement_family": "acceleration", "target_cfc": "CFC 180"},
                {"body_region": "neck", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "neck", "measurement_family": "moment", "target_cfc": "CFC 600"},
                {"body_region": "femur", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "tibia", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "tibia", "measurement_family": "moment", "target_cfc": "CFC 600"},
                {"body_region": "iliac", "measurement_family": "force", "target_cfc": "CFC 600"},
                {"body_region": "iliac", "measurement_family": "moment", "target_cfc": "CFC 600"},
                {"body_region": "knee", "measurement_family": "slider_displacement", "target_cfc": "CFC 180"},
            ),
        },
    },
}


def get_filter_preset_profile(mode, dummy_profile):
    resolved_mode, resolved_profile = resolve_dummy_profile_key(dummy_profile, test_mode=mode)
    profile = (FILTER_PRESET_DB.get(resolved_mode) or {}).get(resolved_profile)
    if not profile:
        return None
    result = deepcopy(profile)
    result["mode"] = resolved_mode
    result["dummy_profile"] = resolved_profile
    return result
