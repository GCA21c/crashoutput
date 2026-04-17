import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from .excel_summary_mapping import (
    EXCEL_IARV_EXPORT_RULES,
    EXCEL_RESULT_SOURCE_OVERRIDES,
    EXCEL_VALUE_EXPORT_RULES,
    SUMMARY_CRITERIA_ALIASES,
    SUMMARY_META_FIELDS,
    SUMMARY_OCCUPANT_LABEL_CELLS,
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


def format_excel_numeric_value(value, decimals=2):
    if value is None:
        return None
    try:
        quantized = Decimal(str(value)).quantize(Decimal("1").scaleb(-int(decimals)), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    return f"{quantized:.{int(decimals)}f}"


def round_for_excel_export(value, decimals=2):
    return format_excel_numeric_value(value, decimals=decimals)


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


def _occupant_label(slot_info):
    name = str((slot_info or {}).get("dummy_name") or "").strip()
    profile = str((slot_info or {}).get("dummy_profile") or "").strip()
    if name and profile:
        return f"{name} - {profile}"
    return name or profile or None


def _template_alias_candidates(region, template_label):
    mapping = SUMMARY_CRITERIA_ALIASES.get(region, {})
    candidates = [template_label]
    candidates.extend(mapping.get(template_label, ()))
    return tuple(_normalize_text(candidate) for candidate in candidates if str(candidate or "").strip())


def should_export_iarv(regulation_name, region, criteria_label):
    rule = EXCEL_IARV_EXPORT_RULES.get(str(regulation_name or "").strip(), {})
    excluded = {
        (str(item_region).strip().upper(), _normalize_text(item_label))
        for item_region, item_label in rule.get("exclude", set())
    }
    return (str(region or "").strip().upper(), _normalize_text(criteria_label)) not in excluded


def transform_excel_export_value(regulation_name, region, criteria_label, value, value_kind):
    if value is None:
        return None
    rule = EXCEL_VALUE_EXPORT_RULES.get(str(regulation_name or "").strip(), {})
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


def _result_source_row(regulation_name, slot_rows, region, template_label, default_row):
    rule = EXCEL_RESULT_SOURCE_OVERRIDES.get(str(regulation_name or "").strip(), {})
    source_labels = rule.get((str(region or "").strip().upper(), str(template_label or "").strip()), ())
    for label in source_labels:
        row = slot_rows.get((str(region or "").strip().upper(), _normalize_text(label)))
        if row:
            return row
    return default_row


def _target_coordinate(ws, target_cell):
    if target_cell is None:
        return None
    target = _top_left_cell(ws, target_cell.row, target_cell.column)
    return target.coordinate


def _record_cell_value(cell_values, ws, target_cell, value):
    coordinate = _target_coordinate(ws, target_cell)
    if not coordinate:
        return False
    cell_values[coordinate] = value
    return True


def _worksheet_archive_name(workbook, ws):
    path = str(getattr(ws, "path", "") or "").lstrip("/")
    if path and "None" not in path:
        return path
    try:
        index = list(workbook.worksheets).index(ws) + 1
    except Exception:
        index = 1
    return f"xl/worksheets/sheet{index}.xml"


def _set_cell_xml_value(cell, value):
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for child_name in ("v", "is"):
        child = cell.find(f"{ns}{child_name}")
        if child is not None:
            cell.remove(child)
    if value is None:
        cell.attrib.pop("t", None)
        return
    cell.set("t", "inlineStr")
    inline = ET.SubElement(cell, f"{ns}is")
    text = ET.SubElement(inline, f"{ns}t")
    text.text = str(value)
    if text.text != text.text.strip():
        text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _patch_sheet_values_only(template_path, output_path, worksheet_archive_name, cell_values):
    cell_values = {str(coord): value for coord, value in dict(cell_values or {}).items()}
    shutil.copyfile(template_path, output_path)
    if not cell_values:
        return

    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    ET.register_namespace("", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

    with zipfile.ZipFile(output_path, "r") as archive:
        try:
            sheet_xml = archive.read(worksheet_archive_name)
        except KeyError as exc:
            raise ExcelExportError(f"Worksheet XML not found in template: {worksheet_archive_name}") from exc

    root = ET.fromstring(sheet_xml)
    cells = {cell.get("r"): cell for cell in root.findall(f".//{ns}c") if cell.get("r")}
    missing = [coord for coord in cell_values if coord not in cells]
    if missing:
        raise ExcelExportError(f"Excel template is missing expected input cells: {', '.join(missing)}")
    for coord, value in cell_values.items():
        _set_cell_xml_value(cells[coord], value)
    patched_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with zipfile.ZipFile(output_path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
        for item in source.infolist():
            data = patched_xml if item.filename == worksheet_archive_name else source.read(item.filename)
            target.writestr(item, data)
    temp_path.replace(output_path)


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

    cell_values = {}
    written_meta = 0
    for spec in SUMMARY_META_FIELDS:
        label_cell = _find_anchor_cell(worksheet, spec["template_anchor"])
        target_cell = _next_input_cell(worksheet, label_cell) if label_cell is not None else None
        if _record_cell_value(cell_values, worksheet, target_cell, dict(report_fields or {}).get(spec["field_key"]) or None):
            written_meta += 1

    written_occupants = 0
    for cell_ref, slot_info in zip(SUMMARY_OCCUPANT_LABEL_CELLS, list((snapshot or {}).get("slots") or [])):
        if _record_cell_value(cell_values, worksheet, worksheet[cell_ref], _occupant_label(slot_info)):
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
            for candidate_key in _template_alias_candidates(region, str(template_label or "")):
                matched = slot_rows.get((region, candidate_key))
                if matched:
                    break
            if not matched:
                missing.append(f"{slot} {region} {template_label}")
                continue
            iarv_cell = worksheet.cell(row=template_row, column=column_group["iarv_column"])
            result_cell = worksheet.cell(row=template_row, column=column_group["result_column"])
            if should_export_iarv(regulation_name, region, matched.get("label")):
                iarv_value = transform_excel_export_value(regulation_name, region, matched.get("label"), matched.get("limit"), "iarv")
                _record_cell_value(cell_values, worksheet, iarv_cell, format_excel_numeric_value(iarv_value))
            else:
                _record_cell_value(cell_values, worksheet, iarv_cell, None)
            result_source = _result_source_row(regulation_name, slot_rows, region, template_label, matched)
            result_value = transform_excel_export_value(regulation_name, region, matched.get("label"), result_source.get("value"), "result")
            _record_cell_value(cell_values, worksheet, result_cell, format_excel_numeric_value(result_value))
            written_results += 1

    _patch_sheet_values_only(template, output, _worksheet_archive_name(workbook, worksheet), cell_values)
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
