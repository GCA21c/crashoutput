"""AUTO SET preset matching helpers for DATA FILTERING."""

from app.core.dummy import get_filter_preset_profile
from app.services.preprocessing.service import get_numeric_channels


def is_rd_aux_channel(channel_meta):
    parsed = dict((channel_meta or {}).get("isocode_parsed") or {})
    fine_1 = str(parsed.get("fine_location_1") or "").strip().upper()
    fine_2 = str(parsed.get("fine_location_2") or "").strip().upper()
    if fine_1 == "RD" or fine_2 == "RD":
        return True
    for key in ("raw_isocode", "managed_isocode"):
        code = str((channel_meta or {}).get(key) or "").strip().upper()
        if len(code) == 16 and (code[6:8] == "RD" or code[8:10] == "RD"):
            return True
    return False


def preset_measurement_family(channel, channel_meta):
    parsed = dict((channel_meta or {}).get("isocode_parsed") or {})
    data_type = str(parsed.get("data_type_code") or "").strip().upper()
    sensor = str((channel_meta or {}).get("sensor_family") or parsed.get("sensor_location") or "").strip().lower()
    main_location = str(parsed.get("main_location_code") or "").strip().upper()
    if data_type == "AC":
        return "acceleration"
    if data_type == "FO":
        return "force"
    if data_type == "MO":
        return "moment"
    if data_type == "DS":
        if sensor == "knee" and main_location in ("KNSL", "KNEE"):
            return "slider_displacement"
        if sensor == "chest":
            return "deflection"
        return "displacement"

    # Some legacy files have incomplete ISO parse metadata but still carry
    # useful channel descriptions from the loader.
    text = " ".join((
        str(channel or ""),
        str((channel_meta or {}).get("description") or ""),
        str((channel_meta or {}).get("unit") or ""),
    )).lower()
    if "acc" in text or "accel" in text:
        return "acceleration"
    if "force" in text or "load" in text:
        return "force"
    if "moment" in text:
        return "moment"
    if "knee" in text and ("slider" in text or "disp" in text):
        return "slider_displacement"
    if "chest" in text and ("def" in text or "disp" in text):
        return "deflection"
    return ""


def channel_matches_preset_rule(channel, channel_meta, slot, rule):
    parsed = dict((channel_meta or {}).get("isocode_parsed") or {})
    channel_slot = str(
        (channel_meta or {}).get("dummy_position")
        or parsed.get("dummy_position_normalized")
        or ""
    ).strip().upper()
    if channel_slot != slot:
        return False
    sensor = str((channel_meta or {}).get("sensor_family") or parsed.get("sensor_location") or "").strip().lower()
    if sensor != str(rule.get("body_region") or "").strip().lower():
        return False
    return preset_measurement_family(channel, channel_meta) == str(rule.get("measurement_family") or "").strip().lower()


def build_auto_filter_map(config, active_df, time_column, channel_meta):
    config = dict(config or {})
    mode = str(config.get("injury_test_mode") or "-").strip().upper()
    if not config.get("setup_complete") or mode == "-":
        return {}, ["TEST SETUP이 완료되지 않았습니다."], []

    if active_df is None or time_column is None:
        return {}, ["먼저 DAT 데이터를 로드하세요."], []

    numeric_channels = set(get_numeric_channels(active_df, time_column))
    channel_meta = dict(channel_meta or {})
    active_positions = [
        str(slot).strip().upper()
        for slot in (config.get("active_positions") or [])
        if str(slot).strip().upper().startswith("B")
    ]
    slot_meta = dict(config.get("slot_meta") or {})
    channel_to_filter = {}
    missing = []
    unsupported = []

    for slot in active_positions:
        profile_name = str((slot_meta.get(slot) or {}).get("dummy_profile") or "").strip()
        preset = get_filter_preset_profile(mode, profile_name)
        if not preset:
            unsupported.append(f"{slot}:{profile_name or '-'}")
            continue
        for rule in preset.get("rules", ()):
            matched = []
            for channel in numeric_channels:
                meta = dict(channel_meta.get(channel) or {})
                if str(meta.get("lineage_type") or "").strip().lower() == "derived":
                    continue
                if is_rd_aux_channel(meta):
                    continue
                if channel_matches_preset_rule(channel, meta, slot, rule):
                    matched.append(channel)
            if not matched:
                missing.append(f"{rule.get('body_region', '-').upper()} {rule.get('measurement_family', '-')} for {slot}")
                continue
            for channel in matched:
                target_cfc = str(rule.get("target_cfc") or "").strip()
                current_cfc = str((channel_meta.get(channel) or {}).get("current_filter_label") or "Raw").strip()
                if current_cfc != target_cfc:
                    channel_to_filter[channel] = target_cfc

    if unsupported:
        missing.append(f"unsupported preset profile: {', '.join(unsupported)}")
    return {channel: label for channel, label in channel_to_filter.items() if label}, missing, unsupported
