import re
from pathlib import Path

from .excel_summary_mapping import (
    SUMMARY_CRITERIA_ALIASES,
    SUMMARY_META_FIELDS,
    SUMMARY_TEMPLATE_PATH,
)


class ExcelExportError(RuntimeError):
    pass


def _load_openpyxl():
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ExcelExportError("openpyxl is required for Excel export. Install openpyxl and retry.") from exc
    return load_workbook


def _normalize_text(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"^[●\-\s]+", "", text)
    text = text.replace("*", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _display_value(value):
    if value is None:
        return None
    try:
        numeric = float(value)
    except Exception:
        return str(value)
    return numeric


def _worksheet_cells(ws):
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                yield cell


def _cell_range_for(ws, cell):
    for merged_range in ws.merged_cells.ranges:
        if cell.coordinate in merged_range:
            return merged_range
    return None


def _top_left_cell(ws, row, column):
    cell = ws.cell(row=row, column=column)
    merged_range = _cell_range_for(ws, cell)
    if merged_range is not None:
        return ws.cell(row=merged_range.min_row, column=merged_range.min_col)
    return cell


def _next_input_cell(ws, label_cell):
    label_range = _cell_range_for(ws, label_cell)
    start_column = (label_range.max_col + 1) if label_range is not None else (label_cell.column + 1)
    for column in range(start_column, ws.max_column + 1):
        target = _top_left_cell(ws, label_cell.row, column)
        if target.column < column:
            continue
        return target
    return None


def _find_anchor_cell(ws, anchor_text):
    target = _normalize_text(anchor_text)
    for cell in _worksheet_cells(ws):
        if target and target in _normalize_text(cell.value):
            return cell
    return None


def _find_table_header(ws):
    for row in range(1, ws.max_row + 1):
        headers = {}
        for column in range(1, ws.max_column + 1):
            text = _normalize_text(ws.cell(row=row, column=column).value)
            if text == "iarv":
                headers.setdefault("iarv", []).append(column)
            elif text == "result":
                headers.setdefault("result", []).append(column)
        if headers.get("iarv") and headers.get("result"):
            return row, headers
    raise ExcelExportError("Could not find IARV/RESULT headers in the Excel template.")


def _detect_occupant_columns(ws):
    _header_row, headers = _find_table_header(ws)
    groups = []
    result_columns = list(headers.get("result") or [])
    for index, iarv_column in enumerate(headers.get("iarv") or []):
        result_column = next((col for col in result_columns if col > iarv_column), None)
        if result_column is not None:
            groups.append({"index": index, "iarv_column": iarv_column, "result_column": result_column})
    if not groups:
        raise ExcelExportError("Could not detect paired IARV/RESULT columns in the Excel template.")
    return groups


def _section_for_row(ws, row):
    for current_row in range(row, 0, -1):
        value = ws.cell(row=current_row, column=1).value
        normalized = _normalize_text(value)
        if normalized:
            return str(value).strip().upper()
    return ""


def _criteria_rows(ws):
    rows = {}
    for row in range(1, ws.max_row + 1):
        label = ws.cell(row=row, column=2).value
        if label is None:
            continue
        region = _section_for_row(ws, row)
        if not region:
            continue
        rows[(region, _normalize_text(label))] = row
    return rows


def _summary_rows_by_slot(snapshot):
    slots = [slot.get("slot") for slot in (snapshot.get("slots") or []) if slot.get("slot")]
    grouped = {slot: {} for slot in slots}
    for row in snapshot.get("rows") or []:
        slot = row.get("slot")
        if slot not in grouped:
            grouped[slot] = {}
            slots.append(slot)
        region = str(row.get("region") or row.get("section_key") or "").strip().upper()
        label = _normalize_text(row.get("label"))
        grouped[slot][(region, label)] = row
    return slots, grouped


def _template_alias_candidates(region, template_label):
    mapping = SUMMARY_CRITERIA_ALIASES.get(region, {})
    candidates = [template_label]
    candidates.extend(mapping.get(template_label, ()))
    return tuple(_normalize_text(candidate) for candidate in candidates if str(candidate or "").strip())


def _copy_cell_value(ws, target_cell, value):
    if target_cell is None:
        return False
    target = _top_left_cell(ws, target_cell.row, target_cell.column)
    target.value = value
    return True


def export_summary_report_to_excel(snapshot, report_fields, output_path, template_path=None):
    load_workbook = _load_openpyxl()

    template = Path(template_path or SUMMARY_TEMPLATE_PATH)
    if not template.exists():
        raise ExcelExportError(f"Excel template not found: {template}")

    output = Path(output_path)
    if not output.parent.exists():
        raise ExcelExportError(f"Export directory does not exist: {output.parent}")

    workbook = load_workbook(template)
    worksheet = workbook.active

    written_meta = 0
    for spec in SUMMARY_META_FIELDS:
        label_cell = _find_anchor_cell(worksheet, spec["template_anchor"])
        target_cell = _next_input_cell(worksheet, label_cell) if label_cell is not None else None
        if _copy_cell_value(worksheet, target_cell, dict(report_fields or {}).get(spec["field_key"]) or None):
            written_meta += 1

    occupant_columns = _detect_occupant_columns(worksheet)
    template_rows = _criteria_rows(worksheet)
    slots, rows_by_slot = _summary_rows_by_slot(snapshot or {})

    written_results = 0
    missing = []
    skipped_slots = max(0, len(slots) - len(occupant_columns))
    for slot, column_group in zip(slots, occupant_columns):
        slot_rows = rows_by_slot.get(slot) or {}
        for (region, template_label_key), template_row in template_rows.items():
            template_label = worksheet.cell(row=template_row, column=2).value
            matched = None
            for candidate_key in _template_alias_candidates(region, str(template_label or "")):
                matched = slot_rows.get((region, candidate_key))
                if matched:
                    break
            if not matched:
                missing.append(f"{slot} {region} {template_label}")
                continue
            iarv_cell = worksheet.cell(row=template_row, column=column_group["iarv_column"])
            result_cell = worksheet.cell(row=template_row, column=column_group["result_column"])
            _copy_cell_value(worksheet, iarv_cell, _display_value(matched.get("limit")))
            _copy_cell_value(worksheet, result_cell, _display_value(matched.get("value")))
            written_results += 1

    workbook.save(output)
    return {
        "template_path": str(template),
        "output_path": str(output),
        "sheet": worksheet.title,
        "meta_fields_written": written_meta,
        "result_rows_written": written_results,
        "slots_exported": min(len(slots), len(occupant_columns)),
        "slots_available": len(slots),
        "skipped_slots": skipped_slots,
        "missing": missing,
    }
