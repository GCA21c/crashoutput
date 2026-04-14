from app.core.dummy.engine import get_dummy_module_factors

from .definitions import get_regulation_definition
from .excel_mapping import build_excel_mapping


def _as_float(value):
    try:
        result = float(value)
    except Exception:
        return None
    return result if result == result else None


def _candidate_paths(item):
    value_key = str(item.get("value_key") or "").strip()
    aliases = [str(path).strip() for path in (item.get("payload_aliases") or ()) if str(path or "").strip()]
    return tuple(path for path in (value_key, *aliases) if path)


def _read_path(container, path):
    current = container
    for part in str(path or "").split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def _extract_from_container(container, paths, source_name):
    container = dict(container or {})
    for path in paths:
        value = _as_float(_read_path(container, path))
        if value is not None:
            return value, source_name, path
    return None


def _extract_metric_value(item, slot_payload):
    slot_payload = dict(slot_payload or {})
    candidate_paths = _candidate_paths(item)
    for source_name, container in (
        ("report_values", slot_payload.get("report_values")),
        ("structured_metrics", slot_payload.get("structured_metrics")),
        ("top_level", slot_payload),
    ):
        extracted = _extract_from_container(container, candidate_paths, source_name)
        if extracted:
            return extracted
    return None, "missing", ""


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
    value = _as_float(value)
    limit = _as_float(limit)
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
            value, value_source, value_path = _extract_metric_value(item, slot_payload)
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
                "value_path": value_path,
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
