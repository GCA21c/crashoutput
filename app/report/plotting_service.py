from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.report.plotting_config import (
    COMMON_REPORT_FIELD_ORDER,
    PLOTTING_CACHE_KEY,
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
        for graph_key, graph_label in graph_specs:
            graph_uid = slot_payload.get("graph_uid") if slot_payload.get("graph_key") == graph_key else getattr(page, "_injury_graph_uid")(slot, graph_key)
            item = {
                "item_key": _plot_item_key(page_key, slot, graph_key),
                "page_key": page_key,
                "section_key": section_key,
                "slot": slot,
                "graph_key": graph_key,
                "graph_label": graph_label,
                "graph_uid": graph_uid,
                "result_uid": slot_payload.get("result_uid") or "",
                "dummy_name": slot_payload.get("dummy_name") or "",
                "dummy_profile": slot_payload.get("dummy_profile") or slot_payload.get("criterion_key") or "",
                "summary_text": summary_text,
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
    return items


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
    return options


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
    return f"{source_name}{PLOTTING_OUTPUT_SUFFIX}.pptx"


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
    return str(item.get("summary_text") or "-").strip() or "-"


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

