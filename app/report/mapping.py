from app.core.dummy.engine import get_dummy_module_factors

from .definitions import get_regulation_definition
from .excel_mapping import build_excel_mapping


def _as_float(value):
    try:
        result = float(value)
    except Exception:
        return None
    return result if result == result else None


def _structured_metric_value(payload, module_key, value_key):
    payload = dict(payload or {})
    report_values = dict(payload.get("report_values") or {})
    if value_key in report_values:
        return _as_float(report_values.get(value_key))
    structured_metrics = dict(payload.get("structured_metrics") or {})
    if value_key in structured_metrics:
        return _as_float(structured_metrics.get(value_key))
    if module_key == "head":
        if value_key == "hic15":
            return _as_float(payload.get("hic15_value"))
        if value_key == "hic36":
            return _as_float(payload.get("hic36_value"))
        if value_key == "head_3ms_clip":
            return _as_float(payload.get("one_peak_3ms_value"))
    if module_key == "chest":
        if value_key == "chest_3ms_clip":
            return _as_float(payload.get("one_peak_3ms_g"))
        if value_key == "displacement_peak_mm":
            return _as_float(payload.get("displacement_peak_mm"))
    if module_key == "femur":
        if value_key == "left_peak_axial_force_n":
            return _as_float(payload.get("left_peak_axial_force_n"))
        if value_key == "right_peak_axial_force_n":
            return _as_float(payload.get("right_peak_axial_force_n"))
    if module_key == "neck":
        if value_key == "overall_nij":
            return _as_float(payload.get("overall_nij"))
        if value_key == "peak_tension_fz":
            return _as_float(payload.get("peak_tension_fz"))
        if value_key == "peak_compression_fz":
            return _as_float(payload.get("peak_compression_fz"))
    return None


def _extract_metric_value(item, slot_payload):
    value = _structured_metric_value(slot_payload, item.get("module_key"), item.get("value_key"))
    if value is not None:
        return value, "payload"
    return None, "missing"


def _resolve_limit_value(item, slot_payload, test_mode):
    explicit_limit = item.get("limit_value")
    if explicit_limit is not None:
        return _as_float(explicit_limit), "definition"
    profile_name = (
        slot_payload.get("criterion_key")
        or slot_payload.get("dummy_profile")
        or ""
    )
    module_key = item.get("module_key")
    factors = get_dummy_module_factors(profile_name, module_key, test_mode=test_mode)
    if not factors:
        return None, "missing"
    limit_value = _as_float(factors.get(item.get("limit_key")))
    return limit_value, "dummy_profile"


def _evaluate_status(value, limit, comparison):
    if value is None:
        return "MISSING"
    if limit is None:
        return "N/A"
    if comparison == "<=":
        return "PASS" if value <= (limit + 1e-12) else "FAIL"
    if comparison == ">=":
        return "PASS" if value >= (limit - 1e-12) else "FAIL"
    return "N/A"


def _shared_slot_meta(metadata):
    config = dict(metadata.get("shared_dummy_config") or {})
    return dict(config.get("slot_meta") or {})


def _resolve_slots(metadata, injury_saved):
    config = dict(metadata.get("shared_dummy_config") or {})
    slots = [slot for slot in (config.get("active_positions") or []) if isinstance(slot, str)]
    if not slots:
        seen = []
        for section_payload in dict(injury_saved or {}).values():
            for slot in dict((section_payload or {}).get("slots") or {}).keys():
                if slot not in seen:
                    seen.append(slot)
        slots = seen
    return slots or ["B1"]


def _slot_payload(injury_saved, section_key, slot):
    section_payload = dict((injury_saved.get(section_key) or {}) if isinstance(injury_saved, dict) else {})
    return dict((section_payload.get("slots") or {}).get(slot) or {})


def _slot_identity(slot, slot_payload, slot_meta):
    payload = dict(slot_payload or {})
    meta = dict(slot_meta or {})
    dummy_name = payload.get("dummy_name") or meta.get("dummy_name") or ""
    return {
        "slot": slot,
        "dummy_name": dummy_name,
        "dummy_profile": payload.get("dummy_profile") or payload.get("criterion_key") or meta.get("dummy_profile") or "",
        "slot_label": f"{slot} - {dummy_name}" if dummy_name else slot,
    }


def build_report_snapshot(metadata, regulation_name):
    metadata = dict(metadata or {})
    definition = get_regulation_definition(regulation_name)
    if not definition:
        return {
            "regulation_name": regulation_name,
            "definition": None,
            "slots": [],
            "rows": [],
            "excel_mapping": {},
            "value_count": 0,
        }

    injury_saved = dict(metadata.get("injury_saved_results") or {})
    slot_meta_map = _shared_slot_meta(metadata)
    test_mode = str((metadata.get("shared_dummy_config") or {}).get("injury_test_mode") or "FRONTAL").strip().upper() or "FRONTAL"
    slots = _resolve_slots(metadata, injury_saved)

    slot_info = []
    for slot in slots:
        exemplar = {}
        for item in definition.get("items", ()):
            exemplar = _slot_payload(injury_saved, item.get("section_key"), slot)
            if exemplar:
                break
        slot_info.append(_slot_identity(slot, exemplar, slot_meta_map.get(slot)))

    rows = []
    value_count = 0
    for item in definition.get("items", ()):
        for slot in slots:
            slot_payload = _slot_payload(injury_saved, item.get("section_key"), slot)
            value, value_source = _extract_metric_value(item, slot_payload)
            limit, limit_source = _resolve_limit_value(item, slot_payload, test_mode)
            status = _evaluate_status(value, limit, item.get("comparison"))
            if value is not None:
                value_count += 1
            identity = _slot_identity(slot, slot_payload, slot_meta_map.get(slot))
            rows.append({
                "slot": slot,
                "slot_label": identity["slot_label"],
                "dummy_name": identity["dummy_name"],
                "dummy_profile": identity["dummy_profile"],
                "section_key": item.get("section_key"),
                "result_key": item.get("result_key"),
                "label": item.get("label"),
                "unit": item.get("unit") or "",
                "value": value,
                "limit": limit,
                "status": status,
                "comparison": item.get("comparison"),
                "result_uid": slot_payload.get("result_uid") or "",
                "value_source": value_source,
                "limit_source": limit_source,
            })

    excel_mapping = build_excel_mapping(definition["label"], [slot["slot"] for slot in slot_info])
    return {
        "regulation_name": definition["label"],
        "definition": definition,
        "slots": slot_info,
        "rows": rows,
        "excel_mapping": excel_mapping,
        "value_count": value_count,
    }
