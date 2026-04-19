"""DATA OFFSET preview overlay persistence helpers."""


OFFSET_PREVIEW_BEFORE_METADATA_KEY = "offset_preview_before_df"
OFFSET_PREVIEW_AFTER_METADATA_KEY = "offset_preview_after_df"
OFFSET_PREVIEW_METADATA_KEY = OFFSET_PREVIEW_BEFORE_METADATA_KEY


def _copy_dataframe(value):
    if value is None:
        return None
    try:
        return value.copy(deep=True)
    except Exception:
        return None


def copy_offset_preview_from_metadata(metadata):
    return _copy_dataframe(dict(metadata or {}).get(OFFSET_PREVIEW_BEFORE_METADATA_KEY))


def copy_offset_after_preview_from_metadata(metadata):
    return _copy_dataframe(dict(metadata or {}).get(OFFSET_PREVIEW_AFTER_METADATA_KEY))


def offset_preview_metadata(before_df, after_df=None):
    metadata = {}
    before = _copy_dataframe(before_df)
    after = _copy_dataframe(after_df)
    if before is not None:
        metadata[OFFSET_PREVIEW_BEFORE_METADATA_KEY] = before
    if after is not None:
        metadata[OFFSET_PREVIEW_AFTER_METADATA_KEY] = after
    return metadata


def rename_offset_preview_columns(metadata, rename_map):
    metadata = dict(metadata or {})
    if not rename_map:
        return metadata
    for key in (OFFSET_PREVIEW_BEFORE_METADATA_KEY, OFFSET_PREVIEW_AFTER_METADATA_KEY):
        preview_df = metadata.get(key)
        if preview_df is None:
            continue
        try:
            metadata[key] = preview_df.rename(columns=dict(rename_map))
        except Exception:
            pass
    return metadata
