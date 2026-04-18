"""Occupant slot helpers for report metadata assembly."""


def normalize_slot_key(slot):
    return str(slot or "").strip().upper()


def occupant_label(slot_info):
    name = str((slot_info or {}).get("dummy_name") or "").strip()
    profile = str((slot_info or {}).get("dummy_profile") or "").strip()
    if name and profile:
        return f"{name} - {profile}"
    return name or profile or None


def dummy_name_from_slot_label(slot_label, slot):
    text = str(slot_label or "").strip()
    slot_key = normalize_slot_key(slot)
    if not text:
        return ""
    prefix = f"{slot_key} - "
    if slot_key and text.upper().startswith(prefix.upper()):
        return text[len(prefix):].strip()
    if " - " in text:
        left, right = text.split(" - ", 1)
        if normalize_slot_key(left) == slot_key:
            return right.strip()
    return ""


def occupant_slots_from_config(config):
    config = dict(config or {})
    slot_meta = dict(config.get("slot_meta") or {})
    ordered_slots = []
    for slot in list(config.get("active_positions") or []) + list(config.get("row_positions") or []):
        slot_key = normalize_slot_key(slot)
        if slot_key and slot_key not in ordered_slots:
            ordered_slots.append(slot_key)
    for slot, meta in slot_meta.items():
        slot_key = normalize_slot_key(slot)
        if not slot_key or slot_key in ordered_slots:
            continue
        meta = dict(meta or {})
        if str(meta.get("dummy_name") or "").strip() or str(meta.get("dummy_profile") or "").strip():
            ordered_slots.append(slot_key)
    result = []
    for slot_key in ordered_slots:
        meta = dict(slot_meta.get(slot_key) or {})
        result.append({
            "slot": slot_key,
            "dummy_name": str(meta.get("dummy_name") or "").strip(),
            "dummy_profile": str(meta.get("dummy_profile") or "").strip(),
        })
    return result


def merge_occupant_slots(*slot_groups):
    merged = {}
    order = []
    for group in slot_groups:
        for info in list(group or []):
            info = dict(info or {})
            slot_key = normalize_slot_key(info.get("slot"))
            if not slot_key:
                continue
            if slot_key not in merged:
                merged[slot_key] = {"slot": slot_key, "dummy_name": "", "dummy_profile": ""}
                order.append(slot_key)
            current = merged[slot_key]
            dummy_name = str(info.get("dummy_name") or "").strip()
            dummy_profile = str(info.get("dummy_profile") or "").strip()
            if dummy_name and not current["dummy_name"]:
                current["dummy_name"] = dummy_name
            if dummy_profile and not current["dummy_profile"]:
                current["dummy_profile"] = dummy_profile
    return [merged[slot] for slot in order]


def occupant_slot_infos_from_snapshot(snapshot, report_fields):
    report_slots = list(dict(report_fields or {}).get("occupant_slots") or [])
    snapshot_slots = list((snapshot or {}).get("slots") or [])
    row_slots = []
    for row in list((snapshot or {}).get("rows") or []):
        row = dict(row or {})
        slot_key = normalize_slot_key(row.get("slot"))
        dummy_name = str(row.get("dummy_name") or "").strip() or dummy_name_from_slot_label(row.get("slot_label"), slot_key)
        dummy_profile = str(row.get("dummy_profile") or row.get("criterion_key") or "").strip()
        row_slots.append({
            "slot": slot_key,
            "dummy_name": dummy_name,
            "dummy_profile": dummy_profile,
        })
    return [
        slot_info
        for slot_info in merge_occupant_slots(report_slots, snapshot_slots, row_slots)
        if occupant_label(slot_info)
    ]
