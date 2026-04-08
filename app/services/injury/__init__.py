"""Injury service package.

Avoid eager submodule imports here because preprocessing.service imports
app.services.injury.common_engines during its own module initialization.
Eagerly importing head/chest/neck modules from package __init__ creates a
circular import chain:

preprocessing.service -> injury.common_engines -> injury.__init__
-> head_injury -> preprocessing.service

Expose the public callables via thin lazy wrappers instead.
"""


def build_head_injury_bundle(*args, **kwargs):
    from .head_injury import build_head_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_neck_injury_bundle(*args, **kwargs):
    from .neck_injury import calculate_neck_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_chest_injury_bundle(*args, **kwargs):
    from .chest_injury import calculate_chest_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_femur_injury_bundle(*args, **kwargs):
    from .femur_injury import calculate_femur_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_pelvis_injury_bundle(*args, **kwargs):
    from .pelvis_injury import calculate_pelvis_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_knee_injury_bundle(*args, **kwargs):
    from .knee_injury import calculate_knee_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_iliac_injury_bundle(*args, **kwargs):
    from .iliac_injury import calculate_iliac_injury_bundle as _impl
    return _impl(*args, **kwargs)


def calculate_tibia_injury_bundle(*args, **kwargs):
    from .tibia_injury import calculate_tibia_injury_bundle as _impl
    return _impl(*args, **kwargs)


__all__ = [
    'build_head_injury_bundle',
    'calculate_neck_injury_bundle',
    'calculate_chest_injury_bundle',
    'calculate_femur_injury_bundle',
    'calculate_pelvis_injury_bundle',
    'calculate_knee_injury_bundle',
    'calculate_iliac_injury_bundle',
    'calculate_tibia_injury_bundle',
]
