"""Dataset metadata assembly helpers for persistence paths."""


def build_dataset_snapshot_metadata(
    base_metadata,
    *,
    source_file_path,
    history,
    history_entries,
    shared_dummy_config,
    time_column,
    units,
    descriptions,
    channel_filter_labels,
    pre_filter_reference_df,
    pre_filter_reference_time_column,
    metadata_override=None,
):
    metadata = dict(base_metadata or {})
    if metadata_override:
        metadata.update(dict(metadata_override))
    metadata["source_format"] = "PICKLE"
    metadata["source_file_path"] = source_file_path
    metadata["saved_history"] = list(history or [])
    metadata["saved_history_entries"] = list(history_entries or [])
    metadata["shared_dummy_config"] = dict(shared_dummy_config or {})
    metadata["time_column"] = time_column or metadata.get("time_column")
    metadata["units"] = dict(units or {})
    metadata["descriptions"] = dict(descriptions or {})
    metadata["channel_filter_labels"] = dict(channel_filter_labels or {})
    metadata["pre_filter_reference_df"] = (
        pre_filter_reference_df.copy(deep=True)
        if pre_filter_reference_df is not None else None
    )
    metadata["pre_filter_reference_time_column"] = (
        pre_filter_reference_time_column
        or time_column
        or metadata.get("time_column")
    )
    return metadata
