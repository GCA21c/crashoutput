"""DATA OFFSET preview overlay persistence helpers."""


OFFSET_PREVIEW_METADATA_KEY = "offset_preview_before_df"


def copy_offset_preview_from_metadata(metadata):
    before = dict(metadata or {}).get(OFFSET_PREVIEW_METADATA_KEY)
    if before is None:
        return None
    try:
        return before.copy(deep=True)
    except Exception:
        return None


def offset_preview_metadata(before_df):
    if before_df is None:
        return {}
    try:
        return {OFFSET_PREVIEW_METADATA_KEY: before_df.copy(deep=True)}
    except Exception:
        return {}


def rename_offset_preview_columns(metadata, rename_map):
    metadata = dict(metadata or {})
    preview_df = metadata.get(OFFSET_PREVIEW_METADATA_KEY)
    if preview_df is None or not rename_map:
        return metadata
    try:
        metadata[OFFSET_PREVIEW_METADATA_KEY] = preview_df.rename(columns=dict(rename_map))
    except Exception:
        pass
    return metadata
