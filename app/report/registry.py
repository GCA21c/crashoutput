from .rules import REPORT_RULES, get_report_rule, get_report_rule_choices
from .templates import REPORT_TEMPLATE_SPECS, get_report_template_spec


def get_regulation_choices():
    return get_report_rule_choices()


def get_regulation_definition(name):
    return get_report_rule(name)


REGULATION_DEFINITIONS = REPORT_RULES


__all__ = [
    "REGULATION_DEFINITIONS",
    "REPORT_RULES",
    "REPORT_TEMPLATE_SPECS",
    "get_regulation_choices",
    "get_regulation_definition",
    "get_report_rule",
    "get_report_rule_choices",
    "get_report_template_spec",
]
