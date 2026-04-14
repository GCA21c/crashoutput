from .fmvss208 import FMVSS_208_DEFINITION, FMVSS_208_NAME


REGULATION_DEFINITIONS = {
    FMVSS_208_NAME: FMVSS_208_DEFINITION,
}


def get_regulation_choices():
    return tuple(REGULATION_DEFINITIONS.keys())


def get_regulation_definition(name):
    return REGULATION_DEFINITIONS.get(str(name or "").strip())
