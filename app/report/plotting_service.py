from __future__ import annotations

import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

from app.core.utils.formatting import fmt_metric_at, fmt_metric_range, fmt_time_ms, fmt_value
from app.report.plotting_config import (
    COMMON_REPORT_FIELD_ORDER,
    PLOTTING_CACHE_KEY,
    PLOTTING_GRAPH_TEXT_RULES,
    PLOTTING_OUTPUT_SUFFIX,
    PLOTTING_SAVE_SUFFIX,
    PLOTTING_TEMPLATE_PATH,
)


PLOTTING_MODULE_ORDER = (
    ("hic", "head"),
    ("nij", "neck"),
    ("chest", "chest"),
    ("pelvis", "pelvis"),
    ("femur", "femur"),
    ("knee", "knee"),
    ("iliac", "iliac"),
    ("tibia", "tibia"),
)

_SLOT_ORDER = {slot: index for index, slot in enumerate(("B1", "B2", "B3", "B4", "B5", "B6"))}
_MODULE_ORDER = {section_key: index for index, (_page_key, section_key) in enumerate(PLOTTING_MODULE_ORDER)}


def plotting_payload_from_metadata(metadata):
    metadata = dict(metadata or {})
    report_saved = dict(metadata.get("report_saved_results") or {})
    return dict(report_saved.get(PLOTTING_CACHE_KEY) or {})


def update_plotting_cache(metadata, payload):
    metadata = dict(metadata or {})
    report_saved = dict(metadata.get("report_saved_results") or {})
    report_saved[PLOTTING_CACHE_KEY] = dict(payload or {})
    metadata["report_saved_results"] = report_saved
    return metadata


def plotting_report_fields(workbench):
    metadata = dict(getattr(workbench, "dataset_metadata", {}) or {})
    report_saved = dict(metadata.get("report_saved_results") or {})
    summary_saved = dict(report_saved.get("summary_report") or {})
    fields = dict(summary_saved.get("report_fields") or {})
    if all(str(fields.get(key) or "").strip() for key, _label in COMMON_REPORT_FIELD_ORDER):
        return fields
    summary_page = (getattr(workbench, "pages", {}) or {}).get("report_summary")
    if summary_page is not None and hasattr(summary_page, "_report_input_variables"):
        for key, variable in summary_page._report_input_variables().items():
            fields[key] = str(variable.get() or "").strip()
    return fields


def format_common_report_text(fields):
    fields = dict(fields or {})
    lines = []
    for key, label in COMMON_REPORT_FIELD_ORDER:
        value = str(fields.get(key) or "").strip() or "-"
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _plot_item_key(page_key, slot, graph_key):
    return f"{page_key}|{slot}|{graph_key}"


def _compact_metric_detail(detail):
    detail = dict(detail or {})
    compact = {}
    for key in ("value", "time_s", "start_time_s", "end_time_s", "start_time", "end_time", "duration_ms", "status"):
        if key in detail:
            compact[key] = detail.get(key)
    return compact


def _build_auto_text_context(section_key, slot_payload):
    slot_payload = dict(slot_payload or {})
    context = {
        "channels": dict(slot_payload.get("channels") or {}),
        "report_values": dict(slot_payload.get("report_values") or {}),
        "metric_extrema": dict(slot_payload.get("metric_extrema") or {}),
        "slot": str(slot_payload.get("slot") or ""),
    }
    if section_key == "head":
        context["details"] = {
            key: slot_payload.get(key)
            for key in (
                "hic15_value", "hic15_start_time_s", "hic15_end_time_s",
                "hic36_value", "hic36_start_time_s", "hic36_end_time_s",
                "one_peak_3ms_value", "one_peak_3ms_start_time_s", "one_peak_3ms_end_time_s",
                "multiple_peak_3ms_value", "multiple_peak_3ms_start_time_s", "multiple_peak_3ms_end_time_s",
                "resultant_peak_value", "resultant_peak_time_s",
                "fmvss_head_acc_80g_3ms_duration_ms", "fmvss_head_acc_80g_3ms_status",
            )
        }
    else:
        structured = dict(slot_payload.get("structured_metrics") or {})
        details = {}
        for key in (
            "one_peak_3ms_detail", "multiple_peak_3ms_detail", "resultant_peak",
            "one_peak_3ms", "multiple_peak_3ms",
        ):
            details[key] = _compact_metric_detail(structured.get(key))
        context["details"] = details
    return context


def _axis_display_name(axis_key, channel_name):
    axis = str(axis_key or "").upper()
    channel_text = str(channel_name or "").strip()
    return f"ACC {axis} - {channel_text}" if channel_text else f"ACC {axis} - -"


def _axis_extrema_lines(axis_key, unit, context):
    channels = dict(context.get("channels") or {})
    metric_extrema = dict(context.get("metric_extrema") or {})
    channel_name = channels.get(axis_key) or ""
    lookup_key = {
        "x": ("head_x", "x_g", "x_plot"),
        "y": ("head_y", "y_g", "y_plot"),
        "z": ("head_z", "z_g", "z_plot"),
    }.get(str(axis_key or "").lower(), tuple())
    detail = None
    for key in lookup_key:
        if key in metric_extrema:
            detail = dict(metric_extrema.get(key) or {})
            break
    return [
        _axis_display_name(axis_key, channel_name),
        f"Max : {fmt_value((detail or {}).get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('max_time_s'))}",
        f"Min : {fmt_value((detail or {}).get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('min_time_s'))}",
    ]


def _resultant_extrema_lines(resultant_label, resultant_key, unit, context):
    metric_extrema = dict(context.get("metric_extrema") or {})
    detail = dict(metric_extrema.get(resultant_key) or {})
    return [
        f"{resultant_label} MAX: {fmt_value(detail.get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms(detail.get('max_time_s'))}",
        f"{resultant_label} MIN: {fmt_value(detail.get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms(detail.get('min_time_s'))}",
    ]


def _injury_line_from_rule(line_rule, context):
    report_values = dict(context.get("report_values") or {})
    details = dict(context.get("details") or {})
    kind = str((line_rule or {}).get("type") or "").strip().lower()
    label = str((line_rule or {}).get("label") or "").strip()
    unit = str((line_rule or {}).get("unit") or "")
    def _value_from_rule(key_name):
        return report_values.get(key_name) if report_values.get(key_name) is not None else details.get(key_name)
    if kind == "range":
        return fmt_metric_range(
            label,
            _value_from_rule(line_rule.get("value_key")),
            unit=unit,
            start_s=details.get(line_rule.get("start_key")),
            end_s=details.get(line_rule.get("end_key")),
        )
    if kind == "at":
        return fmt_metric_at(
            label,
            _value_from_rule(line_rule.get("value_key")),
            unit=unit,
            time_s=details.get(line_rule.get("time_key")),
        )
    if kind in {"detail_range", "range_detail"}:
        detail = dict(details.get(line_rule.get("detail_key")) or {})
        return fmt_metric_range(label, detail.get("value"), unit=unit, start_s=detail.get("start_time_s"), end_s=detail.get("end_time_s"))
    if kind == "detail_at":
        detail = dict(details.get(line_rule.get("detail_key")) or {})
        return fmt_metric_at(label, detail.get("value"), unit=unit, time_s=detail.get("time_s"))
    if kind == "fmvss_head_80g":
        slot = str(context.get("slot") or "-")
        status = str(details.get("fmvss_head_acc_80g_3ms_status") or "-")
        duration_ms = details.get("fmvss_head_acc_80g_3ms_duration_ms")
        duration_text = "-"
        if duration_ms is not None:
            duration_text = f"{float(duration_ms):.4f}".rstrip("0").rstrip(".")
            if "." not in duration_text:
                duration_text = f"{duration_text}.0"
            duration_text = f"{duration_text}ms"
        return "\n".join([
            f"[{slot} - FMVSS Head Acceleration 80g / 3ms Limit]",
            f"  - Result : {status} ({duration_text})",
        ])
    return "-"


def build_plotting_auto_text(item):
    item = dict(item or {})
    section_key = str(item.get("section_key") or "")
    graph_key = str(item.get("graph_key") or "")
    rule = dict(PLOTTING_GRAPH_TEXT_RULES.get((section_key, graph_key)) or {})
    if not rule:
        return str(item.get("summary_text") or "-").strip() or "-"
    context = dict(item.get("auto_text_context") or {})
    template = str(rule.get("template") or "").strip().lower()
    lines = []
    if template in {"acc_axes", "acc_axes_then_injuries"}:
        axis_keys = tuple(rule.get("axis_keys") or ())
        for axis_key in axis_keys:
            lines.extend(_axis_extrema_lines(axis_key, rule.get("unit") or "g", context))
        if template == "acc_axes_then_injuries":
            lines.extend(_resultant_extrema_lines(rule.get("resultant_label") or "Resultant", rule.get("resultant_key") or "resultant", rule.get("unit") or "g", context))
            lines.append("- Injuries -")
            for line_rule in tuple(rule.get("injury_lines") or ()):
                lines.append(_injury_line_from_rule(line_rule, context))
    elif template == "acc_resultant_with_injuries":
        lines.extend(_resultant_extrema_lines(rule.get("resultant_label") or "Resultant", rule.get("resultant_key") or "resultant", rule.get("unit") or "g", context))
        lines.append("- Injuries -")
        for line_rule in tuple(rule.get("injury_lines") or ()):
            lines.append(_injury_line_from_rule(line_rule, context))
    text = "\n".join(line for line in lines if line is not None).strip()
    return text or (str(item.get("summary_text") or "-").strip() or "-")


def _collect_page_plot_items(workbench, page_key, section_key):
    page = (getattr(workbench, "pages", {}) or {}).get(page_key)
    if page is None:
        return []
    metadata = dict(getattr(workbench, "dataset_metadata", {}) or {})
    injury_saved = dict(metadata.get("injury_saved_results") or {})
    section_payload = dict(injury_saved.get(section_key) or {})
    slots_payload = dict(section_payload.get("slots") or {})
    if not slots_payload:
        return []
    items = []
    for slot in [slot for slot in ("B1", "B2", "B3", "B4", "B5", "B6") if slot in slots_payload]:
        slot_payload = dict(slots_payload.get(slot) or {})
        can_render = bool(getattr(page, "_ensure_slot_plot_data")(slot))
        summary_text = str(slot_payload.get("summary_text") or "-").strip() or "-"
        graph_specs = list(getattr(page, "_graph_tab_specs")() or [])
        for graph_order, (graph_key, graph_label) in enumerate(graph_specs):
            graph_uid = slot_payload.get("graph_uid") if slot_payload.get("graph_key") == graph_key else getattr(page, "_injury_graph_uid")(slot, graph_key)
            item = {
                "item_key": _plot_item_key(page_key, slot, graph_key),
                "page_key": page_key,
                "section_key": section_key,
                "slot": slot,
                "graph_key": graph_key,
                "graph_label": graph_label,
                "graph_order": graph_order,
                "graph_uid": graph_uid,
                "result_uid": slot_payload.get("result_uid") or "",
                "dummy_name": slot_payload.get("dummy_name") or "",
                "dummy_profile": slot_payload.get("dummy_profile") or slot_payload.get("criterion_key") or "",
                "summary_text": summary_text,
                "auto_text_context": _build_auto_text_context(section_key, slot_payload),
                "text_mode": "auto",
                "custom_text": "",
                "included": True,
                "loaded": bool(can_render),
                "status_text": "Loaded" if can_render else "Missing",
            }
            items.append(item)
    return items


def collect_plot_items(workbench):
    items = []
    for page_key, section_key in PLOTTING_MODULE_ORDER:
        items.extend(_collect_page_plot_items(workbench, page_key, section_key))
    return sorted(
        items,
        key=lambda item: (
            _SLOT_ORDER.get(str(item.get("slot") or "").strip().upper(), len(_SLOT_ORDER)),
            _MODULE_ORDER.get(str(item.get("section_key") or "").strip().lower(), len(_MODULE_ORDER)),
            int(item.get("graph_order") or 0),
            str(item.get("graph_label") or item.get("graph_key") or ""),
        ),
    )


def merge_plot_items(existing_payload, collected_items):
    existing_payload = dict(existing_payload or {})
    existing_items = {
        str(item.get("item_key")): dict(item)
        for item in list(existing_payload.get("items") or [])
        if str(item.get("item_key") or "").strip()
    }
    merged = []
    seen = set()
    existing_order = [str(item.get("item_key")) for item in list(existing_payload.get("items") or []) if str(item.get("item_key") or "").strip()]
    collected_map = {str(item.get("item_key")): dict(item) for item in list(collected_items or [])}
    for item_key in existing_order:
        fresh = dict(collected_map.get(item_key) or {})
        if not fresh:
            continue
        previous = dict(existing_items.get(item_key) or {})
        fresh["included"] = bool(previous.get("included", True))
        fresh["text_mode"] = str(previous.get("text_mode") or "auto")
        fresh["custom_text"] = str(previous.get("custom_text") or "")
        merged.append(fresh)
        seen.add(item_key)
    for item in collected_items or []:
        item_key = str(item.get("item_key") or "")
        if item_key in seen:
            continue
        merged.append(dict(item))
        seen.add(item_key)
    return merged


def available_plot_options(all_items, current_items):
    current_keys = {str(item.get("item_key")) for item in list(current_items or [])}
    options = []
    for item in all_items or []:
        item_key = str(item.get("item_key") or "")
        if item_key and item_key not in current_keys:
            options.append(dict(item))
    return sorted(
        options,
        key=lambda item: (
            _SLOT_ORDER.get(str(item.get("slot") or "").strip().upper(), len(_SLOT_ORDER)),
            _MODULE_ORDER.get(str(item.get("section_key") or "").strip().lower(), len(_MODULE_ORDER)),
            int(item.get("graph_order") or 0),
            str(item.get("graph_label") or item.get("graph_key") or ""),
        ),
    )


def build_plotting_payload(items, report_fields, template_path=None):
    return {
        "report_type": PLOTTING_CACHE_KEY,
        "template_path": str(template_path or PLOTTING_TEMPLATE_PATH),
        "report_fields": dict(report_fields or {}),
        "items": [dict(item) for item in list(items or [])],
    }


def plotting_save_suffix():
    return PLOTTING_SAVE_SUFFIX


def plotting_default_template_path():
    return str(PLOTTING_TEMPLATE_PATH)


def plotting_output_default_name(source_path):
    source_name = Path(str(source_path or "plotting")).stem
    safe_name = re.sub(r'[\\/:*?"<>|]+', "_", str(source_name)).strip() or "plotting"
    return f"{safe_name}{PLOTTING_OUTPUT_SUFFIX}.pptx"


def plotting_output_name_from_fields(report_fields, source_path=None):
    report_fields = dict(report_fields or {})
    test_id = str(report_fields.get("test_id") or "").strip()
    if test_id:
        safe_name = re.sub(r'[\\/:*?"<>|]+', "_", test_id).strip() or "plotting"
        return f"{safe_name}{PLOTTING_OUTPUT_SUFFIX}.pptx"
    return plotting_output_default_name(source_path)


def plotting_item_display_name(item):
    item = dict(item or {})
    slot = str(item.get("slot") or "-")
    dummy_name = str(item.get("dummy_name") or "").strip()
    graph_label = str(item.get("graph_label") or item.get("graph_key") or "-")
    if dummy_name:
        return f"{slot} | {dummy_name} | {graph_label}"
    return f"{slot} | {graph_label}"


def plotting_item_text(item):
    item = dict(item or {})
    if str(item.get("text_mode") or "auto").lower() == "custom":
        custom = str(item.get("custom_text") or "").strip()
        if custom:
            return custom
    return build_plotting_auto_text(item)


def render_plot_image(workbench, item, output_path):
    item = dict(item or {})
    page = (getattr(workbench, "pages", {}) or {}).get(item.get("page_key"))
    if page is None:
        raise RuntimeError(f"Plot page not found: {item.get('page_key')}")
    slot = str(item.get("slot") or "").strip()
    graph_key = str(item.get("graph_key") or "").strip()
    if not slot or not graph_key:
        raise RuntimeError("Invalid plot item.")
    previous_slot = page._active_slot() if hasattr(page, "_active_slot") else None
    if hasattr(page, "active_dummy_var"):
        try:
            page.active_dummy_var.set(slot)
        except Exception:
            pass
    if not getattr(page, "_ensure_slot_plot_data")(slot):
        raise RuntimeError(f"Plot data missing for {slot} {graph_key}")
    if page.initial_mode == "hic":
        page.show_hic_bundle_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "nij":
        page.show_neck_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "chest":
        page.show_chest_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "pelvis":
        page.show_pelvis_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "femur":
        page.show_femur_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "knee":
        page.show_knee_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "iliac":
        page.show_iliac_graph(graph_key, slot=slot, silent=True)
    elif page.initial_mode == "tibia":
        page.show_tibia_graph(graph_key, slot=slot, silent=True)
    else:
        raise RuntimeError(f"Unsupported plot mode: {page.initial_mode}")
    page.figure.savefig(output_path, dpi=180, bbox_inches="tight")
    if previous_slot and hasattr(page, "active_dummy_var"):
        try:
            page.active_dummy_var.set(previous_slot)
        except Exception:
            pass
    return str(output_path)


@contextmanager
def rendered_plot_images(workbench, items):
    rendered = []
    with tempfile.TemporaryDirectory(prefix="crashoutput_plotting_") as tmpdir:
        temp_dir = Path(tmpdir)
        for index, item in enumerate(list(items or []), start=1):
            if not bool(item.get("included", True)):
                continue
            file_name = f"{index:03d}_{str(item.get('item_key') or 'plot').replace('|', '_')}.png"
            image_path = temp_dir / file_name
            render_plot_image(workbench, item, image_path)
            rendered.append((dict(item), image_path))
        yield rendered
