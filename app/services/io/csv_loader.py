from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd


class CsvLoadError(Exception):
    pass


def _read_text(csv_path: Path) -> str:
    last_error = None
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8", "latin-1"):
        try:
            return csv_path.read_text(encoding=enc)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise CsvLoadError(f"CSV 인코딩을 해석할 수 없습니다: {last_error}")
    raise CsvLoadError("CSV 파일을 읽을 수 없습니다.")


def _detect_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        lines = [line for line in sample.splitlines() if line.strip()]
        if not lines:
            return ","
        candidates = [",", ";", "\t", "|"]
        scores = []
        for delim in candidates:
            counts = [line.count(delim) for line in lines[:20]]
            scores.append((sum(counts), delim))
        scores.sort(reverse=True)
        return scores[0][1] if scores and scores[0][0] > 0 else ","


def _rows_from_text(text: str, delimiter: str) -> List[List[str]]:
    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    rows = []
    for row in reader:
        rows.append([str(cell).strip() for cell in row])
    return rows


def rows_to_preview_dataframe(rows: List[List[str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    width = max(len(r) for r in rows)
    padded = [r + [""] * (width - len(r)) for r in rows]
    return pd.DataFrame(padded, dtype=object)


def _clean_header_name(value: str, fallback_idx: int) -> str:
    name = str(value or "").strip()
    return name if name else f"Column_{fallback_idx + 1}"


def _make_unique(names: List[str]) -> List[str]:
    used = {}
    unique = []
    for name in names:
        base = name
        count = used.get(base, 0)
        if count == 0:
            unique.append(base)
        else:
            unique.append(f"{base}_{count + 1}")
        used[base] = count + 1
    return unique


def _is_time_like(value: str) -> bool:
    txt = str(value or "").strip().lower()
    if not txt:
        return False
    return txt == "time" or txt.startswith("time[") or txt.startswith("time (") or txt.startswith("time_") or "time" in txt

def _find_header_row(rows: List[List[str]]) -> int:

    for idx, row in enumerate(rows):
        row_text = " | ".join(str(cell).strip().lower() for cell in row[:5])
        if "iso channel code" in row_text:
            return idx

    for idx, row in enumerate(rows):
        if any(_is_time_like(cell) for cell in row):
            return idx

    best_idx = 0
    best_score = -1
    for idx, row in enumerate(rows[:20]):
        nonempty = sum(1 for cell in row if str(cell).strip())
        if nonempty > best_score:
            best_score = nonempty
            best_idx = idx
    return best_idx

def _find_time_column(columns: List[str]) -> str | None:
    for col in columns:
        if str(col).strip().lower() == "time":
            return col
    for col in columns:
        if "time" in str(col).strip().lower():
            return col
    return columns[0] if columns else None


def _find_data_start_row(df: pd.DataFrame, time_column: str | None) -> int | None:
    if df.empty or time_column is None or time_column not in df.columns:
        return None
    arr = pd.to_numeric(df[time_column], errors="coerce").to_numpy(dtype=float)
    valid = np.flatnonzero(np.isfinite(arr))
    if valid.size == 0:
        return None
    return int(valid[0])


def _count_time_numeric_rows(df: pd.DataFrame, time_column: str | None, data_start_row: int | None) -> int:
    if df.empty or time_column is None or time_column not in df.columns:
        return 0
    start = int(data_start_row or 0)
    if start < 0:
        start = 0
    arr = pd.to_numeric(df[time_column], errors="coerce").to_numpy(dtype=float)
    if start >= len(arr):
        return 0
    return int(np.isfinite(arr[start:]).sum())




def load_csv_preview(csv_path: str) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        raise CsvLoadError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
    text = _read_text(path)
    delimiter = _detect_delimiter(text)
    rows = _rows_from_text(text, delimiter)
    return rows_to_preview_dataframe(rows)


def load_csv_file(csv_path: str, hidden_rows: List[int] | None = None) -> Tuple[pd.DataFrame, dict]:
    path = Path(csv_path)
    if not path.exists():
        raise CsvLoadError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

    text = _read_text(path)
    delimiter = _detect_delimiter(text)
    rows = _rows_from_text(text, delimiter)
    if not rows:
        raise CsvLoadError("CSV 파일에 읽을 수 있는 행이 없습니다.")

    hidden = set(int(i) for i in (hidden_rows or []))
    visible_rows = [row for idx, row in enumerate(rows) if idx not in hidden]
    if not visible_rows:
        raise CsvLoadError("모든 행이 숨김 처리되어 로드할 데이터가 없습니다.")

    width = max(len(r) for r in visible_rows)
    padded = [r + [""] * (width - len(r)) for r in visible_rows]

    header_row = _find_header_row(padded)
    headers = _make_unique([_clean_header_name(v, i) for i, v in enumerate(padded[header_row])])
    data_rows = padded[header_row + 1 :]

    df = pd.DataFrame(data_rows, columns=headers, dtype=object)
    if df.empty:
        raise CsvLoadError("헤더 아래에 데이터 행이 없습니다.")

    # Remove columns that are completely empty after header extraction.
    keep_cols = [col for col in df.columns if df[col].astype(str).str.strip().ne("").any()]
    df = df.loc[:, keep_cols].copy()

    time_column = _find_time_column(list(df.columns))
    data_start_row = _find_data_start_row(df, time_column)

    data_length = _count_time_numeric_rows(df, time_column, data_start_row)

    metadata = {
        "source_format": "CSV",
        "source_file_path": str(path),
        "delimiter": delimiter,
        "hidden_rows": sorted(hidden),
        "header_row_in_visible_rows": int(header_row),
        "header_row_original_index": next((i for i in range(len(rows)) if i not in hidden and len([j for j in range(i + 1) if j not in hidden]) - 1 == header_row), None),
        "time_column": time_column,
        "data_start_row": data_start_row,
        "data_row_count": int(data_length),
        "units": {},
        "descriptions": {},
        "lengths": {col: int(data_length) for col in df.columns},
    }
    return df.reset_index(drop=True), metadata
