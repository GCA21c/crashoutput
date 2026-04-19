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
