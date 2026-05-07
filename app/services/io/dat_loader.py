import re
import struct
from pathlib import Path

import numpy as np
import pandas as pd

_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "latin-1")


class DatLoadError(Exception):
    pass


_DTYPE_MAP = {
    "INT8": np.dtype('<i1'),
    "UINT8": np.dtype('<u1'),
    "BYTE": np.dtype('<u1'),
    "INT16": np.dtype('<i2'),
    "UINT16": np.dtype('<u2'),
    "WORD": np.dtype('<u2'),
    "INT32": np.dtype('<i4'),
    "UINT32": np.dtype('<u4'),
    "DWORD": np.dtype('<u4'),
    "INT64": np.dtype('<i8'),
    "UINT64": np.dtype('<u8'),
    "REAL32": np.dtype('<f4'),
    "SINGLE": np.dtype('<f4'),
    "FLOAT": np.dtype('<f4'),
    "REAL64": np.dtype('<f8'),
    "DOUBLE": np.dtype('<f8'),
}

_RAW_PAYLOAD_EXTENSIONS = {".dig"}


def _read_text(file_path: Path) -> str:
    raw = file_path.read_bytes()
    for enc in _TEXT_ENCODINGS:
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _parse_header_blocks(text: str):
    blocks = []
    parts = text.split("#BEGINCHANNELHEADER")
    for part in parts[1:]:
        block_text = part.split("#ENDCHANNELHEADER", 1)[0]
        info = {}
        for line in block_text.splitlines():
            line = line.strip().rstrip("\x00")
            if not line or "," not in line:
                continue
            key, value = line.split(",", 1)
            info[key.strip()] = value.strip()
        if info:
            blocks.append(info)
    return blocks


def _safe_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except Exception:
        return float(default)


def _safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return int(default)




def _extract_standard_label(text: str) -> str:
    patterns = [
        r"\bSAE\s*J\s*211\b",
        r"\bISO\s*6487\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(0).upper()).replace("J ", "J")
    return ""

def _make_unique_names(names):
    used = {}
    result = []
    for name in names:
        base = str(name).strip() or "Channel"
        if base not in used:
            used[base] = 1
            result.append(base)
            continue
        used[base] += 1
        result.append(f"{base}_{used[base]}")
    return result


def _decimal_places_from_text(value_text: str, max_places: int = 12) -> int:
    text = str(value_text or "").strip().lower()
    if not text:
        return 0
    if 'e' in text:
        try:
            number = float(text)
        except Exception:
            return 0
        if not np.isfinite(number) or number == 0.0:
            return 0
        text = f"{number:.12f}".rstrip('0').rstrip('.')
    if '.' not in text:
        return 0
    return max(0, min(max_places, len(text.split('.', 1)[1].rstrip('0'))))


def _parse_chn_file_index(chn_name: str):
    match = re.search(r"Ch(\d+)\.(\d+)\.chn$", str(chn_name or ""), flags=re.IGNORECASE)
    if not match:
        return None
    return {
        "channel": int(match.group(1)),
        "subchannel": int(match.group(2)),
    }


def _build_implicit_channel(block, count):
    # Time-like implicit channels in some DAT exports use 240=start and 241=step,
    # but DAS program DAT samples consistently expose time through 271/272.
    # Prioritizing 272/271 avoids misreading channel scale/offset as time values.
    start_text = block.get("272", block.get("240", 0.0))
    dt_text = block.get("271", block.get("241", 0.0))
    start = _safe_float(start_text, 0.0)
    dt = _safe_float(dt_text, 0.0)
    values = start + np.arange(count, dtype=np.float64) * dt
    # Quantize to the explicit DAT time resolution so later trimming/saving does not
    # expose distracting binary floating-point artifacts such as 0.0199000000003.
    decimals = max(_decimal_places_from_text(start_text), _decimal_places_from_text(dt_text))
    if decimals > 0:
        values = np.round(values, decimals)
    return values.astype(float, copy=False)


def _channel_file_kind(channel_path: Path) -> str:
    suffix = str(channel_path.suffix or "").lower()
    if suffix in _RAW_PAYLOAD_EXTENSIONS:
        return "RAW_PAYLOAD"
    if suffix == ".chn":
        return "CHN"
    return suffix.lstrip(".").upper() or "UNKNOWN"


def _resolve_data_offset(channel_path: Path, raw: bytes, block, dtype, count):
    kind = _channel_file_kind(channel_path)
    exact_payload_size = int(count) * int(dtype.itemsize)
    if kind == "RAW_PAYLOAD":
        return 0, kind
    if kind != "CHN" and exact_payload_size > 0 and len(raw) == exact_payload_size:
        return 0, "RAW_PAYLOAD"

    data_offset = struct.unpack_from("<I", raw, 8)[0] if len(raw) >= 12 else 0
    if data_offset <= 0 or data_offset >= len(raw):
        if exact_payload_size > 0 and len(raw) == exact_payload_size:
            return 0, "RAW_PAYLOAD"
        data_offset = max(0, _safe_int(block.get("221", 0), 0))
    return int(data_offset), kind


def _read_dat_channel_file(channel_path: Path, block, count):
    if not channel_path.exists():
        raise DatLoadError(f"필수 DAT 채널 파일을 찾지 못했습니다: {channel_path.name}")

    raw = channel_path.read_bytes()
    dtype_name = str(block.get("214", "INT16")).strip().upper()
    dtype = _DTYPE_MAP.get(dtype_name)
    if dtype is None:
        raise DatLoadError(f"지원하지 않는 DAT 채널 데이터 형식입니다: {dtype_name}")

    if _channel_file_kind(channel_path) == "CHN" and len(raw) < 32:
        raise DatLoadError(f"DAT CHN 파일 크기가 너무 작습니다: {channel_path.name}")

    data_offset, channel_file_kind = _resolve_data_offset(channel_path, raw, block, dtype, count)

    available_count = (len(raw) - data_offset) // dtype.itemsize
    if available_count <= 0:
        raise DatLoadError(f"DAT 채널 데이터 영역을 해석할 수 없습니다: {channel_path.name}")

    read_count = min(int(count), int(available_count))
    values = np.frombuffer(raw, dtype=dtype, count=read_count, offset=data_offset).astype(np.float64, copy=True)
    actual_count = int(read_count)
    if read_count < count:
        # Keep shape compatibility during load, but preserve the real payload
        # length separately so the viewer can show the true sample count.
        padded = np.zeros(int(count), dtype=np.float64)
        padded[:read_count] = values
        values = padded

    scale = _safe_float(block.get("241", 1.0), 1.0)
    offset = _safe_float(block.get("240", 0.0), 0.0)
    values = offset + values * scale
    read_info = {
        "file_kind": channel_file_kind,
        "data_offset": int(data_offset),
        "dtype": dtype_name,
    }
    return values, actual_count, read_info


def load_dat_file(dat_path):
    dat_path = Path(dat_path)
    if not dat_path.exists():
        raise DatLoadError("DAT 파일을 찾지 못했습니다.")

    text = _read_text(dat_path)
    blocks = _parse_header_blocks(text)
    if not blocks:
        raise DatLoadError("DAT 채널 헤더를 찾지 못했습니다.")

    raw_names = []
    raw_columns = []
    descriptions = {}
    units = {}
    lengths = {}
    actual_lengths = {}
    dat_channel_indices = []
    dat_channel_files = []
    dat_channel_file_indices = []
    dat_channel_novalue_headers = []
    dat_channel_read_infos = []
    time_col_name = None

    for block_index, block in enumerate(blocks, start=1):
        count = _safe_int(block.get("220", 0), 0)
        if count <= 0:
            continue

        channel_name = block.get("200", "").strip() or block.get("201", "").strip() or "Channel"
        description = block.get("201", "").strip()
        unit = block.get("202", "").strip()
        channel_type = block.get("210", "").strip().upper()

        if channel_type == "IMPLICIT":
            values = _build_implicit_channel(block, count)
            actual_count = int(count)
            read_info = {
                "file_kind": "IMPLICIT",
                "data_offset": None,
                "dtype": "IMPLICIT",
            }
            column_name = "Time" if time_col_name is None else channel_name
            chn_name = ""
            if time_col_name is None:
                time_col_name = column_name
        else:
            chn_name = block.get("211", "").strip()
            if not chn_name:
                continue
            chn_path = dat_path.parent / chn_name
            values, actual_count, read_info = _read_dat_channel_file(chn_path, block, count)
            column_name = channel_name

        raw_names.append(column_name)
        raw_columns.append(values)
        dat_channel_indices.append(int(block_index))
        dat_channel_files.append(chn_name)
        dat_channel_file_indices.append(_parse_chn_file_index(chn_name))
        dat_channel_novalue_headers.append(block.get("215", "").strip())
        dat_channel_read_infos.append(read_info)
        descriptions[column_name] = description or column_name
        units[column_name] = unit
        lengths[column_name] = int(count)
        actual_lengths[column_name] = int(actual_count)

    if not raw_columns:
        raise DatLoadError("읽을 수 있는 채널 데이터가 없습니다.")

    unique_names = _make_unique_names(raw_names)
    data = {unique_name: values for unique_name, values in zip(unique_names, raw_columns)}

    unique_descriptions = {}
    unique_units = {}
    unique_lengths = {}
    unique_actual_lengths = {}
    unique_dat_channel_index_map = {}
    unique_dat_channel_file_map = {}
    unique_dat_channel_file_index_map = {}
    unique_dat_channel_novalue_map = {}
    unique_dat_channel_file_type_map = {}
    unique_dat_channel_data_offset_map = {}
    unique_dat_channel_dtype_map = {}
    for raw_name, unique_name, dat_index, chn_name, chn_index, novalue_header, read_info in zip(
        raw_names,
        unique_names,
        dat_channel_indices,
        dat_channel_files,
        dat_channel_file_indices,
        dat_channel_novalue_headers,
        dat_channel_read_infos,
    ):
        unique_descriptions[unique_name] = descriptions.get(raw_name, raw_name)
        unique_units[unique_name] = units.get(raw_name, "")
        unique_lengths[unique_name] = int(lengths.get(raw_name, 0) or 0)
        unique_actual_lengths[unique_name] = int(actual_lengths.get(raw_name, 0) or 0)
        unique_dat_channel_index_map[unique_name] = int(dat_index)
        if chn_name:
            unique_dat_channel_file_map[unique_name] = chn_name
        if chn_index:
            unique_dat_channel_file_index_map[unique_name] = dict(chn_index)
        if novalue_header != "":
            unique_dat_channel_novalue_map[unique_name] = novalue_header
        read_info = dict(read_info or {})
        file_kind = str(read_info.get("file_kind") or "").strip()
        if file_kind:
            unique_dat_channel_file_type_map[unique_name] = file_kind
        if read_info.get("data_offset") is not None:
            unique_dat_channel_data_offset_map[unique_name] = int(read_info.get("data_offset"))
        dtype_name = str(read_info.get("dtype") or "").strip()
        if dtype_name:
            unique_dat_channel_dtype_map[unique_name] = dtype_name

    if time_col_name:
        for raw_name, unique_name in zip(raw_names, unique_names):
            if raw_name == time_col_name:
                time_col_name = unique_name
                break

    common_length_candidates = [int(v) for v in unique_actual_lengths.values() if int(v) > 0]
    common_length = min(common_length_candidates) if common_length_candidates else None
    if common_length is not None:
        data = {name: np.asarray(values)[:common_length] for name, values in data.items()}
        unique_lengths = {name: min(int(unique_actual_lengths.get(name, 0) or 0), common_length) for name in data.keys()}

    df = pd.DataFrame(data)
    if time_col_name and time_col_name in df.columns:
        ordered = [time_col_name] + [c for c in df.columns if c != time_col_name]
        df = df[ordered]

    metadata = {
        "units": unique_units,
        "descriptions": unique_descriptions,
        "lengths": unique_lengths,
        "time_column": time_col_name,
        "standard_label": _extract_standard_label(text),
        "source_format": "DAT",
        "dat_channel_index_map": unique_dat_channel_index_map,
        "dat_channel_file_map": unique_dat_channel_file_map,
        "dat_channel_file_index_map": unique_dat_channel_file_index_map,
        "dat_channel_novalue_map": unique_dat_channel_novalue_map,
        "dat_channel_file_type_map": unique_dat_channel_file_type_map,
        "dat_channel_data_offset_map": unique_dat_channel_data_offset_map,
        "dat_channel_dtype_map": unique_dat_channel_dtype_map,
    }
    return df, metadata
