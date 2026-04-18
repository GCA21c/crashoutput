import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from app.report.occupants import (
    dummy_name_from_slot_label,
    normalize_slot_key,
    occupant_label,
)
from app.report.templates import get_report_template_spec


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


def round_for_excel_export(value, decimals=2):
    if value is None:
        return None
    try:
        quantized = Decimal(str(value)).quantize(Decimal("1").scaleb(-int(decimals)), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    return f"{quantized:.{int(decimals)}f}"


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


def resolve_merged_top_left(ws, cell_ref_or_rowcol):
    if isinstance(cell_ref_or_rowcol, tuple):
        cell = ws.cell(row=int(cell_ref_or_rowcol[0]), column=int(cell_ref_or_rowcol[1]))
    elif hasattr(cell_ref_or_rowcol, "row") and hasattr(cell_ref_or_rowcol, "column"):
        cell = cell_ref_or_rowcol
    else:
        cell = ws[str(cell_ref_or_rowcol)]
    merged_range = _cell_range_for(ws, cell)
    if merged_range is not None:
        return ws.cell(row=merged_range.min_row, column=merged_range.min_col)
    return cell


def _top_left_cell(ws, row, column):
    return resolve_merged_top_left(ws, (row, column))


def _next_input_cell(ws, label_cell):
    label_range = _cell_range_for(ws, label_cell)
    start_column = (label_range.max_col + 1) if label_range is not None else (label_cell.column + 1)
    for column in range(start_column, ws.max_column + 1):
        target = _top_left_cell(ws, label_cell.row, column)
        if target.column < column:
            continue
        return target
    return None


def _next_input_cell_after(ws, value_cell):
    value_range = _cell_range_for(ws, value_cell)
    start_column = (value_range.max_col + 1) if value_range is not None else (value_cell.column + 1)
    for column in range(start_column, ws.max_column + 1):
        target = _top_left_cell(ws, value_cell.row, column)
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


def _occupant_label(slot_info):
    return occupant_label(slot_info)


def _normalize_slot_key(slot):
    return normalize_slot_key(slot)


def _dummy_name_from_slot_label(slot_label, slot):
    return dummy_name_from_slot_label(slot_label, slot)


def _occupant_slot_infos(snapshot, report_fields):
    result = []
    by_slot = {}

    def merge_slot(slot, dummy_name="", dummy_profile=""):
        slot_key = _normalize_slot_key(slot)
        if not slot_key:
            return
        if slot_key not in by_slot:
            by_slot[slot_key] = {"slot": slot_key, "dummy_name": "", "dummy_profile": ""}
            result.append(by_slot[slot_key])
        current = by_slot[slot_key]
        dummy_name = str(dummy_name or "").strip()
        dummy_profile = str(dummy_profile or "").strip()
        if dummy_name and not current["dummy_name"]:
            current["dummy_name"] = dummy_name
        if dummy_profile and not current["dummy_profile"]:
            current["dummy_profile"] = dummy_profile

    for info in list(dict(report_fields or {}).get("occupant_slots") or []):
        info = dict(info or {})
        merge_slot(info.get("slot"), info.get("dummy_name"), info.get("dummy_profile"))
    for info in list((snapshot or {}).get("slots") or []):
        info = dict(info or {})
        merge_slot(info.get("slot"), info.get("dummy_name"), info.get("dummy_profile"))
    for row in list((snapshot or {}).get("rows") or []):
        row = dict(row or {})
        slot_key = _normalize_slot_key(row.get("slot"))
        dummy_name = str(row.get("dummy_name") or "").strip() or _dummy_name_from_slot_label(row.get("slot_label"), slot_key)
        dummy_profile = str(row.get("dummy_profile") or row.get("criterion_key") or "").strip()
        merge_slot(slot_key, dummy_name, dummy_profile)
    return [slot_info for slot_info in result if _occupant_label(slot_info)]


def _occupant_input_cells(ws, template_spec):
    anchor_cell = _find_anchor_cell(ws, "occupant")
    first_cell = _next_input_cell(ws, anchor_cell) if anchor_cell is not None else None
    second_cell = _next_input_cell_after(ws, first_cell) if first_cell is not None else None
    cells = [cell for cell in (first_cell, second_cell) if cell is not None]
    if cells:
        return cells
    return [ws[cell_ref] for cell_ref in template_spec.get("occupant_label_cells", ())]


def _template_alias_candidates(region, template_label, template_spec):
    mapping = template_spec.get("criteria_aliases", {}).get(region, {})
    candidates = [template_label]
    candidates.extend(mapping.get(template_label, ()))
    return tuple(_normalize_text(candidate) for candidate in candidates if str(candidate or "").strip())


def should_export_iarv(regulation_name, region, criteria_label, template_spec=None):
    spec = _active_template_spec(template_spec)
    rule = spec.get("iarv_export_rules", {}).get(str(regulation_name or "").strip(), {})
    excluded = {
        (str(item_region).strip().upper(), _normalize_text(item_label))
        for item_region, item_label in rule.get("exclude", set())
    }
    return (str(region or "").strip().upper(), _normalize_text(criteria_label)) not in excluded


def transform_excel_export_value(regulation_name, region, criteria_label, value, value_kind, template_spec=None):
    if value is None:
        return None
    spec = _active_template_spec(template_spec)
    rule = spec.get("value_export_rules", {}).get(str(regulation_name or "").strip(), {})
    key = (str(region or "").strip().upper(), _normalize_text(criteria_label))
    abs_result = {
        (str(item_region).strip().upper(), _normalize_text(item_label))
        for item_region, item_label in rule.get("abs_result", set())
    }
    if str(value_kind or "").strip().lower() == "result" and key in abs_result:
        try:
            return abs(float(value))
        except Exception:
            return value
    return value


def _result_source_row(regulation_name, slot_rows, region, template_label, default_row, template_spec):
    rule = template_spec.get("result_source_overrides", {}).get(str(regulation_name or "").strip(), {})
    source_labels = rule.get((str(region or "").strip().upper(), str(template_label or "").strip()), ())
    for label in source_labels:
        row = slot_rows.get((str(region or "").strip().upper(), _normalize_text(label)))
        if row:
            return row
    return default_row


def _target_coordinate(ws, target_cell):
    if target_cell is None:
        return None
    target = resolve_merged_top_left(ws, target_cell)
    return target.coordinate


def safe_set_cell_value(ws, target_cell, value):
    coordinate = _target_coordinate(ws, target_cell)
    if not coordinate:
        return False
    ws[coordinate].value = value
    return True


def _active_template_spec(template_spec=None):
    return dict(template_spec or get_report_template_spec())


def export_summary_report_to_excel(snapshot, report_fields, output_path, template_path=None, template_spec=None):
    load_workbook = _load_openpyxl()
    spec = _active_template_spec(template_spec)

    template = Path(template_path or spec.get("template_path"))
    if not template.exists():
        raise ExcelExportError(f"Excel template not found: {template}")

    output = Path(output_path)
    if not output.parent.exists():
        raise ExcelExportError(f"Export directory does not exist: {output.parent}")

    workbook = load_workbook(template)
    worksheet = workbook.active

    written_meta = 0
    for meta_spec in spec.get("meta_fields", ()):
        label_cell = _find_anchor_cell(worksheet, meta_spec["template_anchor"])
        target_cell = _next_input_cell(worksheet, label_cell) if label_cell is not None else None
        if safe_set_cell_value(worksheet, target_cell, dict(report_fields or {}).get(meta_spec["field_key"]) or None):
            written_meta += 1

    written_occupants = 0
    for target_cell, slot_info in zip(_occupant_input_cells(worksheet, spec), _occupant_slot_infos(snapshot or {}, report_fields or {})):
        if safe_set_cell_value(worksheet, target_cell, _occupant_label(slot_info)):
            written_occupants += 1

    occupant_columns = _detect_occupant_columns(worksheet)
    template_rows = _criteria_rows(worksheet)
    slots, rows_by_slot = _summary_rows_by_slot(snapshot or {})
    regulation_name = (snapshot or {}).get("regulation_name") or dict(report_fields or {}).get("regulation") or ""

    written_results = 0
    missing = []
    skipped_slots = max(0, len(slots) - len(occupant_columns))
    for slot, column_group in zip(slots, occupant_columns):
        slot_rows = rows_by_slot.get(slot) or {}
        for (region, template_label_key), template_row in template_rows.items():
            template_label = worksheet.cell(row=template_row, column=2).value
            matched = None
            for candidate_key in _template_alias_candidates(region, str(template_label or ""), spec):
                matched = slot_rows.get((region, candidate_key))
                if matched:
                    break
            if not matched:
                missing.append(f"{slot} {region} {template_label}")
                continue
            iarv_cell = worksheet.cell(row=template_row, column=column_group["iarv_column"])
            result_cell = worksheet.cell(row=template_row, column=column_group["result_column"])
            if should_export_iarv(regulation_name, region, matched.get("label"), spec):
                iarv_value = transform_excel_export_value(regulation_name, region, matched.get("label"), matched.get("limit"), "iarv", spec)
                safe_set_cell_value(worksheet, iarv_cell, round_for_excel_export(iarv_value))
            else:
                safe_set_cell_value(worksheet, iarv_cell, None)
            result_source = _result_source_row(regulation_name, slot_rows, region, template_label, matched, spec)
            result_value = transform_excel_export_value(regulation_name, region, matched.get("label"), result_source.get("value"), "result", spec)
            safe_set_cell_value(worksheet, result_cell, round_for_excel_export(result_value))
            written_results += 1

    workbook.save(output)
    return {
        "template_path": str(template),
        "output_path": str(output),
        "sheet": worksheet.title,
        "meta_fields_written": written_meta,
        "occupant_labels_written": written_occupants,
        "result_rows_written": written_results,
        "slots_exported": min(len(slots), len(occupant_columns)),
        "slots_available": len(slots),
        "skipped_slots": skipped_slots,
        "missing": missing,
    }
