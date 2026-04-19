"""DATA FILTERING application orchestration helpers."""


def normalize_channel_filter_map(channel_to_filter, dataframe_columns):
    columns = set(dataframe_columns) if dataframe_columns is not None else set()
    return {
        str(channel): str(label).strip()
        for channel, label in dict(channel_to_filter or {}).items()
        if str(channel) in columns and str(label).strip()
    }


def filter_application_summary(channel_to_filter, info_prefix):
    channel_to_filter = dict(channel_to_filter or {})
    counts = {}
    for label in channel_to_filter.values():
        counts[label] = counts.get(label, 0) + 1
    count_text = ", ".join(f"{label} {count}개" for label, count in sorted(counts.items()))
    channel_names = sorted(channel_to_filter.keys())
    channel_text = ", ".join(channel_names[:6])
    if len(channel_names) > 6:
        channel_text += f" ... 외 {len(channel_names) - 6}개"
    return f"{info_prefix}: {len(channel_to_filter)}개 채널 preset 적용 ({count_text}) | {channel_text}. [FILTERING!]을 누르면 작업 데이터에 반영됩니다."


def auto_set_no_targets_message(missing):
    text = "AUTO SET 적용 대상이 없습니다."
    missing = list(missing or [])
    if missing:
        text += f" missing: {'; '.join(missing[:8])}"
    return text


def auto_set_details(missing):
    missing = list(missing or [])
    details = []
    if missing:
        details.append(f"missing: {'; '.join(missing[:8])}")
    if len(missing) > 8:
        details.append(f"외 {len(missing) - 8}건")
    return details


def rename_metadata_keys(mapping, rename_map):
    data = dict(mapping or {})
    if not rename_map:
        return data
    return {
        rename_map.get(key, key): value
        for key, value in data.items()
    }


def rename_derived_channel_references(derived_channels, rename_map):
    data = dict(derived_channels or {})
    if not rename_map:
        return data
    out = {}
    for key, value in data.items():
        info = dict(value or {})
        source_channel = str(info.get("source_channel") or "").strip()
        if source_channel:
            info["source_channel"] = rename_map.get(source_channel, source_channel)
        history = []
        for item in list(info.get("filter_history") or []):
            entry = dict(item or {})
            from_channel = str(entry.get("from_channel") or "").strip()
            if from_channel:
                entry["from_channel"] = rename_map.get(from_channel, from_channel)
            history.append(entry)
        if history:
            info["filter_history"] = history
        out[rename_map.get(key, key)] = info
    return out


def filtering_summary_text(filter_labels, limit=6):
    summary_items = [
        f"{channel}={label}"
        for channel, label in dict(filter_labels or {}).items()
        if label != "Raw"
    ]
    summary = ", ".join(summary_items[:limit])
    if len(summary_items) > limit:
        summary += " ..."
    return summary, len(summary_items)


def build_filter_commit_payload(final_descriptions, final_units, final_labels, final_colors, final_derived, pending_count):
    summary, _summary_count = filtering_summary_text(final_labels)
    metadata_override = {
        "descriptions": dict(final_descriptions or {}),
        "units": dict(final_units or {}),
        "channel_filter_labels": dict(final_labels or {}),
        "channel_filter_colors": dict(final_colors or {}),
        "derived_channels": dict(final_derived or {}),
    }
    history_entry = {
        "type": "filtering",
        "message": f"Filtering applied: {summary}",
        "display_message": f"Filtering applied: {int(pending_count)} channel(s)",
    }
    return metadata_override, history_entry
