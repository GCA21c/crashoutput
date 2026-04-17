from .fmvss208_summary import FMVSS208_SUMMARY_TEMPLATE


REPORT_TEMPLATE_SPECS = {
    FMVSS208_SUMMARY_TEMPLATE["key"]: FMVSS208_SUMMARY_TEMPLATE,
}


def get_report_template_spec(key=None):
    if key:
        spec = REPORT_TEMPLATE_SPECS.get(str(key or "").strip())
        if spec:
            return spec
    return FMVSS208_SUMMARY_TEMPLATE
