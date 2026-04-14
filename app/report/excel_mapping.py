from .definitions import get_regulation_definition


REPORT_FIELD_KEYS = ("regulation", "manufacturer", "vehicle", "speed", "test_date", "test_id")


def build_excel_mapping(regulation_name, slots):
    definition = get_regulation_definition(regulation_name)
    mapping = {f"report.{field_key}": "" for field_key in REPORT_FIELD_KEYS}
    if not definition:
        return mapping
    for slot in tuple(slots or ()):
        for item in definition.get("items", ()):
            mapping[f"{definition['key']}.{slot}.{item['result_key']}"] = ""
    return mapping
