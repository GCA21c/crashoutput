from app.core.dummy.engine import get_dummy_module_factors
from app.core.utils.formatting import fmt_range_ms, fmt_time_ms
from app.services.state.injury_result_store import get_payload_store, get_slot_payload

from .registry import get_regulation_definition


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


def _as_float(value):
    try:
        result = float(value)
    except Exception:
        return None
    return result if result == result else None


def _candidate_paths(primary_key, aliases):
    primary = str(primary_key or "").strip()
    alias_values = [str(path).strip() for path in (aliases or ()) if str(path or "").strip()]
    return tuple(path for path in (primary, *alias_values) if path)


def _region_label(item):
    explicit = str(item.get("region") or "").strip()
    if explicit:
        return explicit
    section_key = str(item.get("section_key") or "").strip()
    return section_key.upper() if section_key else "-"


def _apply_transform(value, transform_name):
    numeric = _as_float(value)
    if numeric is None:
        return None
    transform = str(transform_name or "").strip().lower()
    if transform == "abs":
        return abs(numeric)
    return numeric


def _read_path(container, path):
    current = container
    parts = [part for part in str(path or "").split(".") if part]
    if isinstance(current, dict):
        flat_key = ".".join(parts)
        if flat_key in current:
            return current.get(flat_key)
    index = 0
    while index < len(parts):
        if not isinstance(current, dict):
            return None
        remaining = ".".join(parts[index:])
        if remaining in current:
            return current.get(remaining)
        matched = False
        for end in range(len(parts), index, -1):
            candidate = ".".join(parts[index:end])
            if candidate in current:
                current = current.get(candidate)
                index = end
                matched = True
                break
        if matched:
            continue
        current = current.get(parts[index])
        if current is None:
            return None
        index += 1
    return current


def _extract_from_container(container, paths, source_name):
    container = dict(container or {})
    for path in paths:
        value = _as_float(_read_path(container, path))
        if value is not None:
            return value, source_name, path
    return None


def _extract_numeric_field(slot_payload, primary_key, aliases=(), *, transform_name=None):
    slot_payload = dict(slot_payload or {})
    candidate_paths = _candidate_paths(primary_key, aliases)
    for source_name, container in (
        ("report_values", slot_payload.get("report_values")),
        ("structured_metrics", slot_payload.get("structured_metrics")),
        ("top_level", slot_payload),
    ):
        extracted = _extract_from_container(container, candidate_paths, source_name)
        if extracted:
            value, resolved_source, resolved_path = extracted
            return _apply_transform(value, transform_name), resolved_source, resolved_path
    return None, "missing", ""


def _extract_metric_value(item, slot_payload):
    return _extract_numeric_field(
        slot_payload,
        item.get("value_key"),
        item.get("payload_aliases"),
        transform_name=item.get("value_transform"),
    )


def _format_time_text(time_value=None, start_time=None, end_time=None):
    if _as_float(start_time) is not None and _as_float(end_time) is not None:
        return fmt_range_ms(start_time, end_time)
    if _as_float(time_value) is not None:
        return fmt_time_ms(time_value)
    return "-"


def _extract_row_time(item, slot_payload):
    start_value, start_source, start_path = _extract_numeric_field(
        slot_payload,
        item.get("time_start_key"),
        item.get("time_start_aliases"),
    )
    end_value, end_source, end_path = _extract_numeric_field(
        slot_payload,
        item.get("time_end_key"),
        item.get("time_end_aliases"),
    )
    if start_value is not None and end_value is not None:
        source = start_source if start_source == end_source else "mixed"
        path = f"{start_path} ~ {end_path}".strip()
        return {
            "time": _format_time_text(start_time=start_value, end_time=end_value),
            "time_value": None,
            "time_start": start_value,
            "time_end": end_value,
            "time_source": source,
            "time_path": path,
        }
    time_value, time_source, time_path = _extract_numeric_field(
        slot_payload,
        item.get("time_key"),
        item.get("time_aliases"),
    )
    return {
        "time": _format_time_text(time_value=time_value),
        "time_value": time_value,
        "time_start": None,
        "time_end": None,
        "time_source": time_source,
        "time_path": time_path,
    }


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
    return get_slot_payload({ "injury_saved_results": injury_saved }, section_key, slot)


def _slot_identity(slot, slot_payload, slot_meta):
    payload = dict(slot_payload or {})
    meta = dict(slot_meta or {})
    dummy_name = payload.get("dummy_name") or meta.get("dummy_name") or ""
    dummy_profile_display = meta.get("dummy_profile") or payload.get("dummy_profile") or payload.get("criterion_key") or ""
    return {
        "slot": slot,
        "dummy_name": dummy_name,
        "dummy_profile": dummy_profile_display,
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

    injury_saved = get_payload_store(metadata)
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
    for slot in slots:
        for item in definition.get("items", ()):
            slot_payload = _slot_payload(injury_saved, item.get("section_key"), slot)
            value, value_source, value_path = _extract_metric_value(item, slot_payload)
            limit, limit_source = _resolve_limit_value(item, slot_payload, test_mode)
            time_info = _extract_row_time(item, slot_payload)
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
                "region": _region_label(item),
                "result_key": item.get("result_key"),
                "label": item.get("label"),
                "category": item.get("label"),
                "unit": item.get("unit") or "",
                "value": value,
                "time": time_info["time"],
                "time_value": time_info["time_value"],
                "time_start": time_info["time_start"],
                "time_end": time_info["time_end"],
                "limit": limit,
                "status": status,
                "comparison": item.get("comparison"),
                "result_uid": slot_payload.get("result_uid") or "",
                "value_source": value_source,
                "value_path": value_path,
                "time_source": time_info["time_source"],
                "time_path": time_info["time_path"],
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
