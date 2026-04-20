#!/usr/bin/env python3
"""Capture stable regression snapshots from saved CRASH pickle files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.io.dataset_store import DatasetStoreError, load_dataset_pickle  # noqa: E402
from app.report.engine import build_report_snapshot  # noqa: E402


SNAPSHOT_SCHEMA_VERSION = "phase5-regression-v1"
DEFAULT_REGULATION = "FMVSS 208"
VOLATILE_COMPARE_KEYS = {"generated_at_utc", "source_file"}
REPORT_ROW_KEYS = (
    "slot",
    "slot_label",
    "dummy_name",
    "dummy_profile",
    "section_key",
    "region",
    "result_key",
    "label",
    "unit",
    "value",
    "limit",
    "status",
    "comparison",
    "result_uid",
    "value_source",
    "value_path",
    "limit_source",
)


def _install_pandas_pickle_compat() -> None:
    """Allow snapshot capture from saved files with older pandas string indexes."""
    try:
        from pandas.core.arrays.string_ import StringArray
    except Exception:
        return

    original_setstate = getattr(StringArray, "__setstate__", None)
    if getattr(original_setstate, "_crash_snapshot_compat", False):
        return

    def _compat_setstate(self: Any, state: Any) -> None:
        if isinstance(state, tuple) and len(state) == 2:
            _, values = state
            StringArray.__init__(self, values, copy=False)
            return
        if original_setstate is not None:
            original_setstate(self, state)
            return
        raise NotImplementedError(state)

    _compat_setstate._crash_snapshot_compat = True  # type: ignore[attr-defined]
    StringArray.__setstate__ = _compat_setstate


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    return str(value)


def _stable_scalar(value: Any) -> Any:
    safe = _json_safe(value)
    if isinstance(safe, float):
        return round(safe, 12)
    return safe


def _digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _series_digest(series: Any) -> str:
    try:
        import pandas as pd

        hashed = pd.util.hash_pandas_object(series, index=False).values.tobytes()
        return _digest_bytes(hashed)
    except Exception:
        values = [_stable_scalar(value) for value in list(series)]
        payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return _digest_bytes(payload)


def _series_summary(series: Any, include_digest: bool) -> dict[str, Any]:
    summary = {
        "dtype": str(getattr(series, "dtype", type(series).__name__)),
        "count": _json_safe(series.count() if hasattr(series, "count") else len(series)),
        "missing_count": None,
    }
    try:
        summary["missing_count"] = int(series.isna().sum())
    except Exception:
        summary["missing_count"] = None
    if include_digest:
        summary["sha256"] = _series_digest(series)
    try:
        import pandas as pd

        numeric = pd.to_numeric(series, errors="coerce")
        valid = numeric.dropna()
        if len(valid):
            summary.update({
                "min": _json_safe(valid.min()),
                "max": _json_safe(valid.max()),
                "mean": _json_safe(valid.mean()),
                "first": _json_safe(valid.iloc[0]),
                "last": _json_safe(valid.iloc[-1]),
            })
    except Exception:
        pass
    return summary


def _dataframe_summary(dataframe: Any, include_digests: bool) -> dict[str, Any]:
    columns = [str(column) for column in getattr(dataframe, "columns", ())]
    shape = getattr(dataframe, "shape", None)
    summary = {
        "type": type(dataframe).__name__,
        "shape": list(shape) if shape is not None else None,
        "columns": columns,
        "column_count": len(columns),
    }
    if include_digests and columns:
        summary["columns_detail"] = {
            column: _series_summary(dataframe[column], include_digest=True)
            for column in columns
        }
    return summary


def _structure_summary(value: Any, depth: int = 0, max_depth: int = 4) -> Any:
    if depth > max_depth:
        return {"type": type(value).__name__, "truncated": True}
    if hasattr(value, "columns") and hasattr(value, "shape"):
        return _dataframe_summary(value, include_digests=False)
    if isinstance(value, dict):
        keys = [str(key) for key in value.keys()]
        result = {"type": "dict", "keys": sorted(keys), "size": len(keys)}
        if depth < max_depth:
            result["items"] = {
                str(key): _structure_summary(value[key], depth + 1, max_depth)
                for key in sorted(value.keys(), key=lambda item: str(item))
            }
        return result
    if isinstance(value, (list, tuple)):
        return {
            "type": type(value).__name__,
            "size": len(value),
            "items": [_structure_summary(item, depth + 1, max_depth) for item in list(value)[:8]],
            "truncated": len(value) > 8,
        }
    return _json_safe(value)


def _report_snapshot_contract(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in snapshot.get("rows") or ():
        rows.append({key: _json_safe(row.get(key)) for key in REPORT_ROW_KEYS})
    return {
        "regulation_name": snapshot.get("regulation_name"),
        "value_count": snapshot.get("value_count"),
        "slots": _structure_summary(snapshot.get("slots") or []),
        "rows": rows,
        "row_count": len(rows),
        "excel_mapping_keys": sorted((snapshot.get("excel_mapping") or {}).keys()),
    }


def capture_snapshot(dataset_path: Path, regulation: str, include_column_digests: bool) -> dict[str, Any]:
    _install_pandas_pickle_compat()
    loaded = load_dataset_pickle(dataset_path)
    dataframe = loaded.get("dataframe")
    metadata = dict(loaded.get("metadata") or {})
    report_snapshot = build_report_snapshot(metadata, regulation)
    report_saved = dict(metadata.get("report_saved_results") or {})

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(dataset_path),
        "source_label": loaded.get("source_label"),
        "history_length": len(loaded.get("history") or []),
        "dataframe": _dataframe_summary(dataframe, include_digests=include_column_digests),
        "metadata": _structure_summary(metadata),
        "report_snapshot": _report_snapshot_contract(report_snapshot),
        "saved_summary_report": _structure_summary(report_saved.get("summary_report") or {}),
    }


def write_snapshot(snapshot: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _default_output_path(dataset_path: Path) -> Path:
    return REPO_ROOT / "_codex" / "09_regression_snapshots" / f"{dataset_path.stem}_snapshot.json"


def _snapshot_name_for_dataset(dataset_path: Path) -> str:
    return f"{dataset_path.stem}_snapshot.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_values(before: Any, after: Any, path: str, differences: list[str], limit: int) -> None:
    if len(differences) >= limit:
        return
    key = path.rsplit(".", 1)[-1]
    if key in VOLATILE_COMPARE_KEYS:
        return
    if type(before) is not type(after):
        differences.append(f"{path}: type {type(before).__name__} != {type(after).__name__}")
        return
    if isinstance(before, dict):
        before_keys = set(before.keys()) - VOLATILE_COMPARE_KEYS
        after_keys = set(after.keys()) - VOLATILE_COMPARE_KEYS
        for missing in sorted(before_keys - after_keys):
            differences.append(f"{path}.{missing}: missing in after")
            if len(differences) >= limit:
                return
        for added in sorted(after_keys - before_keys):
            differences.append(f"{path}.{added}: added in after")
            if len(differences) >= limit:
                return
        for child_key in sorted(before_keys & after_keys):
            _compare_values(before[child_key], after[child_key], f"{path}.{child_key}", differences, limit)
            if len(differences) >= limit:
                return
        return
    if isinstance(before, list):
        if len(before) != len(after):
            differences.append(f"{path}: length {len(before)} != {len(after)}")
            return
        for index, (before_item, after_item) in enumerate(zip(before, after)):
            _compare_values(before_item, after_item, f"{path}[{index}]", differences, limit)
            if len(differences) >= limit:
                return
        return
    if before != after:
        differences.append(f"{path}: {before!r} != {after!r}")


def compare_snapshots(before_path: Path, after_path: Path, limit: int) -> int:
    before = _load_json(before_path)
    after = _load_json(after_path)
    differences: list[str] = []
    _compare_values(before, after, "snapshot", differences, limit)
    if not differences:
        print("Snapshots match.")
        return 0
    print("Snapshots differ:")
    for item in differences:
        print(f"- {item}")
    if len(differences) >= limit:
        print(f"... stopped after {limit} differences")
    return 1


def capture_directory(input_dir: Path, output_dir: Path, regulation: str, include_column_digests: bool) -> int:
    dataset_paths = sorted(path for path in input_dir.glob("*.pkl") if path.is_file())
    if not dataset_paths:
        print(f"No .pkl files found: {input_dir}", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for dataset_path in dataset_paths:
        output_path = output_dir / _snapshot_name_for_dataset(dataset_path)
        try:
            snapshot = capture_snapshot(
                dataset_path,
                regulation=regulation,
                include_column_digests=include_column_digests,
            )
        except DatasetStoreError as exc:
            failures += 1
            print(f"FAILED {dataset_path}: {exc}", file=sys.stderr)
            continue
        write_snapshot(snapshot, output_path)
        print(f"Snapshot written: {output_path}")
    return 1 if failures else 0


def compare_directories(before_dir: Path, after_dir: Path, limit: int) -> int:
    before_paths = {path.name: path for path in before_dir.glob("*_snapshot.json") if path.is_file()}
    after_paths = {path.name: path for path in after_dir.glob("*_snapshot.json") if path.is_file()}
    exit_code = 0
    for missing in sorted(before_paths.keys() - after_paths.keys()):
        print(f"Missing after snapshot: {missing}")
        exit_code = 1
    for added in sorted(after_paths.keys() - before_paths.keys()):
        print(f"Unexpected after snapshot: {added}")
        exit_code = 1
    for name in sorted(before_paths.keys() & after_paths.keys()):
        print(f"Comparing {name}")
        result = compare_snapshots(before_paths[name], after_paths[name], limit=limit)
        if result:
            exit_code = result
    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture or compare regression snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="capture a snapshot from a saved pickle")
    capture.add_argument("dataset", type=Path, help="saved CRASH pickle path")
    capture.add_argument("--output", type=Path, help="output JSON path")
    capture.add_argument("--regulation", default=DEFAULT_REGULATION, help="report regulation label")
    capture.add_argument(
        "--no-column-digests",
        action="store_true",
        help="skip per-column value digests for faster structure-only snapshots",
    )

    compare = subparsers.add_parser("compare", help="compare two captured snapshots")
    compare.add_argument("before", type=Path, help="baseline snapshot JSON")
    compare.add_argument("after", type=Path, help="new snapshot JSON")
    compare.add_argument("--limit", type=int, default=50, help="maximum differences to print")

    capture_dir = subparsers.add_parser("capture-dir", help="capture snapshots for every .pkl in a directory")
    capture_dir.add_argument("input_dir", type=Path, help="directory containing saved CRASH pickle files")
    capture_dir.add_argument("output_dir", type=Path, help="directory to write snapshot JSON files")
    capture_dir.add_argument("--regulation", default=DEFAULT_REGULATION, help="report regulation label")
    capture_dir.add_argument(
        "--no-column-digests",
        action="store_true",
        help="skip per-column value digests for faster structure-only snapshots",
    )

    compare_dir = subparsers.add_parser("compare-dir", help="compare matching *_snapshot.json files in two directories")
    compare_dir.add_argument("before_dir", type=Path, help="baseline snapshot directory")
    compare_dir.add_argument("after_dir", type=Path, help="new snapshot directory")
    compare_dir.add_argument("--limit", type=int, default=50, help="maximum differences per file to print")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "capture":
        output_path = args.output or _default_output_path(args.dataset)
        try:
            snapshot = capture_snapshot(
                args.dataset,
                regulation=args.regulation,
                include_column_digests=not args.no_column_digests,
            )
        except DatasetStoreError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        write_snapshot(snapshot, output_path)
        print(f"Snapshot written: {output_path}")
        return 0
    if args.command == "compare":
        return compare_snapshots(args.before, args.after, limit=args.limit)
    if args.command == "capture-dir":
        return capture_directory(
            args.input_dir,
            args.output_dir,
            regulation=args.regulation,
            include_column_digests=not args.no_column_digests,
        )
    if args.command == "compare-dir":
        return compare_directories(args.before_dir, args.after_dir, limit=args.limit)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
