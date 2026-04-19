"""Input channel lookup helpers for injury orchestration."""


def find_derived_channel(derived_channels, viewer_columns, source_channel, purpose, role, cfc_value):
    if not source_channel:
        return None
    target_label = f"CFC {int(cfc_value)}"
    viewer_columns = set(viewer_columns) if viewer_columns is not None else set()
    for channel_name, info in dict(derived_channels or {}).items():
        info = dict(info or {})
        if (
            str(info.get("source_channel")) == str(source_channel)
            or str(info.get("root_source_channel")) == str(source_channel)
        ) and (
            str(info.get("role")) == str(role)
            and str(info.get("filter_label")) == target_label
            and str(info.get("purpose")) == str(purpose)
            and channel_name in viewer_columns
        ):
            return channel_name
    return None
