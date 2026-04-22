"""Canonical injury result payload store and lightweight registries.

The persisted payload store remains `injury_saved_results` for compatibility.
This module centralizes read/write helpers so UI, report, plotting, and reload
code can resolve payloads through one path instead of walking ad-hoc metadata.
"""

from __future__ import annotations


PAYLOAD_STORE_KEY = "injury_saved_results"
RESULT_REGISTRY_KEY = "injury_result_registry"
GRAPH_REGISTRY_KEY = "injury_graph_registry"
SLOT_REGISTRY_KEY = "injury_slot_registry"


def _copy_dict(value):
    return dict(value or {})


def get_payload_store(metadata):
    metadata = _copy_dict(metadata)
    return _copy_dict(metadata.get(PAYLOAD_STORE_KEY))


def get_section_payload(metadata, section_key):
    return _copy_dict(get_payload_store(metadata).get(section_key))


def get_slot_payload(metadata, section_key, slot):
    section_payload = get_section_payload(metadata, section_key)
    return _copy_dict(_copy_dict(section_payload.get("slots")).get(slot))


def get_result_registry(metadata):
    metadata = _copy_dict(metadata)
    return _copy_dict(metadata.get(RESULT_REGISTRY_KEY))


def get_graph_registry(metadata):
    metadata = _copy_dict(metadata)
    return _copy_dict(metadata.get(GRAPH_REGISTRY_KEY))


def get_slot_registry(metadata):
    metadata = _copy_dict(metadata)
    registry = metadata.get(SLOT_REGISTRY_KEY)
    return _copy_dict(registry) if isinstance(registry, dict) else {}


def get_result_entry(metadata, result_uid):
    return _copy_dict(get_result_registry(metadata).get(str(result_uid or "").strip()))


def get_graph_entry(metadata, graph_uid):
    return _copy_dict(get_graph_registry(metadata).get(str(graph_uid or "").strip()))


def get_slot_entry(metadata, section_key, slot):
    return _copy_dict(_copy_dict(get_slot_registry(metadata).get(section_key)).get(slot))


def get_payload_by_result_uid(metadata, result_uid):
    entry = get_result_entry(metadata, result_uid)
    if not entry:
        return {}
    return get_slot_payload(metadata, entry.get("section_key"), entry.get("slot"))


def get_payload_by_graph_uid(metadata, graph_uid):
    entry = get_graph_entry(metadata, graph_uid)
    if not entry:
        return {}
    return get_slot_payload(metadata, entry.get("section_key"), entry.get("slot"))


def active_result_uids(metadata, section_key, slot=None):
    if slot:
        entry = get_slot_entry(metadata, section_key, slot)
        return list(entry.get("active_result_uids") or [])
    section_entries = _copy_dict(get_slot_registry(metadata).get(section_key))
    result = []
    for entry in section_entries.values():
        for uid in list(_copy_dict(entry).get("active_result_uids") or []):
            if uid and uid not in result:
                result.append(uid)
    return result


def graph_keys_for_slot(metadata, section_key, slot):
    entry = get_slot_entry(metadata, section_key, slot)
    return list(entry.get("graph_keys") or [])


def iter_slot_payloads(metadata, section_key=None):
    payload_store = get_payload_store(metadata)
    if section_key:
        section_payload = _copy_dict(payload_store.get(section_key))
        for slot, slot_payload in _copy_dict(section_payload.get("slots")).items():
            yield section_key, slot, _copy_dict(slot_payload)
        return
    for current_section, section_payload in payload_store.items():
        for slot, slot_payload in _copy_dict(_copy_dict(section_payload).get("slots")).items():
            yield current_section, slot, _copy_dict(slot_payload)


def _slot_registry_entry(payload):
    payload = _copy_dict(payload)
    result_uid = str(payload.get("result_uid") or "").strip()
    graph_uid = str(payload.get("graph_uid") or "").strip()
    graph_key = str(payload.get("graph_key") or "").strip()
    return {
        "result_uid": result_uid,
        "graph_uid": graph_uid,
        "graph_key": graph_key,
        "active_result_uids": [result_uid] if result_uid else [],
        "graph_keys": [graph_key] if graph_key else [],
        "dummy_name": payload.get("dummy_name") or "",
        "dummy_profile": payload.get("dummy_profile") or payload.get("criterion_key") or "",
    }


def _prune_registry_for_section(registry, section_key):
    registry = _copy_dict(registry)
    kept = {}
    for key, value in registry.items():
        entry = _copy_dict(value)
        if str(entry.get("section_key") or "").strip() == str(section_key or "").strip():
            continue
        kept[key] = entry
    return kept


def _section_slot_registry(slots_payload):
    registry = {}
    for slot, payload in _copy_dict(slots_payload).items():
        registry[slot] = _slot_registry_entry(payload)
    return registry


def _section_result_registry(section_key, slots_payload, source_file_path):
    registry = {}
    for slot, payload in _copy_dict(slots_payload).items():
        payload = _copy_dict(payload)
        uid = str(payload.get("result_uid") or "").strip()
        if not uid:
            continue
        registry[uid] = {
            "section_key": section_key,
            "slot": slot,
            "graph_key": payload.get("graph_key") or "",
            "graph_uid": payload.get("graph_uid") or "",
            "dummy_name": payload.get("dummy_name") or "",
            "dummy_profile": payload.get("dummy_profile") or "",
            "source_file_path": source_file_path or "",
        }
    return registry


def _section_graph_registry(section_key, slots_payload, source_file_path):
    registry = {}
    for slot, payload in _copy_dict(slots_payload).items():
        payload = _copy_dict(payload)
        graph_uid = str(payload.get("graph_uid") or "").strip()
        graph_key = str(payload.get("graph_key") or "").strip()
        result_uid = str(payload.get("result_uid") or "").strip()
        if not (graph_uid and graph_key):
            continue
        registry[graph_uid] = {
            "section_key": section_key,
            "slot": slot,
            "result_uid": result_uid,
            "graph_key": graph_key,
            "dummy_name": payload.get("dummy_name") or "",
            "dummy_profile": payload.get("dummy_profile") or "",
            "source_file_path": source_file_path or "",
            "storage": "rebuild_from_dataset",
        }
    return registry


def _normalized_section_payload(section_payload):
    section_payload = _copy_dict(section_payload)
    slots_payload = {
        slot: _copy_dict(payload)
        for slot, payload in _copy_dict(section_payload.get("slots")).items()
    }
    section_payload["slots"] = slots_payload
    section_payload["result_registry"] = {
        slot: str(_copy_dict(payload).get("result_uid") or "").strip()
        for slot, payload in slots_payload.items()
    }
    return section_payload


def set_section_payload(metadata, section_key, section_payload, *, source_file_path=""):
    metadata = _copy_dict(metadata)
    payload_store = get_payload_store(metadata)
    normalized = _normalized_section_payload(section_payload)
    payload_store[section_key] = normalized
    metadata[PAYLOAD_STORE_KEY] = payload_store

    slots_payload = _copy_dict(normalized.get("slots"))
    result_registry = _prune_registry_for_section(get_result_registry(metadata), section_key)
    result_registry.update(_section_result_registry(section_key, slots_payload, source_file_path))
    metadata[RESULT_REGISTRY_KEY] = result_registry

    graph_registry = _prune_registry_for_section(get_graph_registry(metadata), section_key)
    graph_registry.update(_section_graph_registry(section_key, slots_payload, source_file_path))
    metadata[GRAPH_REGISTRY_KEY] = graph_registry

    slot_registry = get_slot_registry(metadata)
    slot_registry[section_key] = _section_slot_registry(slots_payload)
    metadata[SLOT_REGISTRY_KEY] = slot_registry
    return metadata


def update_slot_payload(metadata, section_key, slot, slot_payload, *, source_file_path=""):
    metadata = _copy_dict(metadata)
    section_payload = get_section_payload(metadata, section_key)
    slots_payload = _copy_dict(section_payload.get("slots"))
    slots_payload[slot] = _copy_dict(slot_payload)
    section_payload["slots"] = slots_payload
    return set_section_payload(metadata, section_key, section_payload, source_file_path=source_file_path)


def update_graph_selection(
    metadata,
    *,
    section_key,
    slot,
    graph_key,
    graph_uid,
    result_uid="",
    dummy_name="",
    dummy_profile="",
    source_file_path="",
):
    metadata = _copy_dict(metadata)
    slot_payload = get_slot_payload(metadata, section_key, slot)
    slot_payload["graph_key"] = graph_key
    slot_payload["graph_uid"] = graph_uid
    if result_uid and not slot_payload.get("result_uid"):
        slot_payload["result_uid"] = result_uid
    if dummy_name and not slot_payload.get("dummy_name"):
        slot_payload["dummy_name"] = dummy_name
    if dummy_profile and not slot_payload.get("dummy_profile"):
        slot_payload["dummy_profile"] = dummy_profile
    return update_slot_payload(metadata, section_key, slot, slot_payload, source_file_path=source_file_path)


def set_active_slot(metadata, section_key, slot):
    metadata = _copy_dict(metadata)
    section_payload = get_section_payload(metadata, section_key)
    if not section_payload:
        return metadata
    section_payload["active_slot"] = slot
    return set_section_payload(metadata, section_key, section_payload, source_file_path=str(metadata.get("source_file_path") or ""))
