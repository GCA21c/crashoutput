from .fmvss208 import FMVSS_208_DEFINITION, FMVSS_208_NAME


REPORT_RULES = {
    FMVSS_208_NAME: FMVSS_208_DEFINITION,
}


def get_report_rule_choices():
    return tuple(REPORT_RULES.keys())


def get_report_rule(name):
    return REPORT_RULES.get(str(name or "").strip())
