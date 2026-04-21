from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from app.report.plotting_config import PLOTTING_TEMPLATE_TEXT_MARKERS
from app.report.plotting_service import plotting_item_display_name, plotting_item_text, rendered_plot_images


class PptExportError(RuntimeError):
    pass


def _load_presentation_api():
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError as exc:
        raise PptExportError("python-pptx is required for PPT export. Install python-pptx and retry.") from exc
    return Presentation, MSO_SHAPE_TYPE


def _shape_text(shape):
    if not getattr(shape, "has_text_frame", False):
        return ""
    parts = []
    for paragraph in list(shape.text_frame.paragraphs):
        text = "".join(run.text for run in list(paragraph.runs))
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _shape_has_marker(shape, marker):
    return marker.lower() in _shape_text(shape).lower()


def _find_marker_shape(slide, marker):
    for shape in list(slide.shapes):
        if _shape_has_marker(shape, marker):
            return shape
    return None


def _set_shape_lines(shape, lines):
    if not getattr(shape, "has_text_frame", False):
        return
    lines = [str(line) for line in list(lines or [])]
    if not lines:
        lines = [""]
    text_frame = shape.text_frame
    while len(text_frame.paragraphs) < len(lines):
        text_frame.add_paragraph()
    paragraphs = list(text_frame.paragraphs)
    for index, paragraph in enumerate(paragraphs):
        target = lines[index] if index < len(lines) else ""
        runs = list(paragraph.runs)
        if runs:
            runs[0].text = target
            for run in runs[1:]:
                run.text = ""
        else:
            paragraph.text = target


def _duplicate_template_slide(presentation, source_slide):
    slide = presentation.slides.add_slide(source_slide.slide_layout)
    sp_tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        sp_tree.remove(shape.element)
    for shape in list(source_slide.shapes):
        sp_tree.insert_element_before(deepcopy(shape.element), "p:extLst")
    return slide


def _report_info_lines(report_fields, item, workbench):
    report_fields = dict(report_fields or {})
    config = getattr(workbench, "get_shared_dummy_config", lambda: {})() or {}
    test_mode = str(config.get("injury_test_mode") or "-").strip().upper() or "-"
    dummy_value = str(item.get("dummy_profile") or item.get("dummy_name") or "-").strip() or "-"
    manufacturer = str(report_fields.get("manufacturer") or "").strip() or "-"
    vehicle = str(report_fields.get("vehicle") or "").strip() or "-"
    speed = str(report_fields.get("speed") or "").strip() or "-"
    test_date = str(report_fields.get("test_date") or "").strip() or "-"
    test_id = str(report_fields.get("test_id") or "").strip() or "-"
    return [
        f"Test ID : {test_id}",
        f"Test Date : {test_date}",
        f"Dummy : {dummy_value}",
        f"Manufacturer : {manufacturer}",
        f"Vehicle : {vehicle}",
        f"Test mode : {test_mode}",
        f"Speed : {speed}",
    ]


def _apply_text_mapping(slide, item, report_fields, workbench):
    test_id = str(dict(report_fields or {}).get("test_id") or "").strip() or "-"
    graph_header = plotting_item_display_name(item)

    title_shape = _find_marker_shape(slide, PLOTTING_TEMPLATE_TEXT_MARKERS["test_id_title"])
    if title_shape is None:
        raise PptExportError("Template marker not found: TEST ID")
    _set_shape_lines(title_shape, [test_id])

    header_shape = _find_marker_shape(slide, PLOTTING_TEMPLATE_TEXT_MARKERS["graph_header"])
    if header_shape is None:
        raise PptExportError("Template marker not found: Graph header name")
    _set_shape_lines(header_shape, [graph_header])

    fields_shape = _find_marker_shape(slide, PLOTTING_TEMPLATE_TEXT_MARKERS["report_fields"])
    if fields_shape is None:
        raise PptExportError("Template marker not found: Test ID :")
    _set_shape_lines(fields_shape, _report_info_lines(report_fields, item, workbench))

    injury_shape = _find_marker_shape(slide, PLOTTING_TEMPLATE_TEXT_MARKERS["injury_text"])
    if injury_shape is None:
        raise PptExportError("Template marker not found: Input txt")
    _set_shape_lines(injury_shape, plotting_item_text(item).splitlines())


def _apply_plot_image(slide, image_path, mso_shape_type):
    plot_shape = _find_marker_shape(slide, PLOTTING_TEMPLATE_TEXT_MARKERS["plot_box"])
    if plot_shape is None:
        raise PptExportError("Template marker not found: Plot here")
    if getattr(plot_shape, "shape_type", None) == mso_shape_type.AUTO_SHAPE:
        try:
            plot_shape.fill.user_picture(str(image_path))
            if getattr(plot_shape, "has_text_frame", False):
                _set_shape_lines(plot_shape, [""])
            return
        except Exception:
            pass
    left = plot_shape.left
    top = plot_shape.top
    width = plot_shape.width
    height = plot_shape.height
    slide.shapes.add_picture(str(image_path), left, top, width=width, height=height)
    if getattr(plot_shape, "has_text_frame", False):
        _set_shape_lines(plot_shape, [""])


def export_plotting_report_to_ppt(workbench, items, report_fields, output_path, template_path):
    Presentation, MSO_SHAPE_TYPE = _load_presentation_api()
    template = Path(str(template_path or "")).expanduser().resolve()
    if not template.exists():
        raise PptExportError(f"PPT template not found: {template}")

    included_items = [dict(item) for item in list(items or []) if bool(item.get("included", True))]
    if not included_items:
        raise PptExportError("No included plots to export.")

    presentation = Presentation(str(template))
    if not presentation.slides:
        raise PptExportError("Template has no slides.")
    template_slide = presentation.slides[0]

    output = Path(str(output_path)).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with rendered_plot_images(workbench, included_items) as rendered_items:
        if not rendered_items:
            raise PptExportError("No rendered plots available for export.")
        slides = [template_slide]
        for _ in rendered_items[1:]:
            slides.append(_duplicate_template_slide(presentation, template_slide))

        for slide, (item, image_path) in zip(slides, rendered_items):
            _apply_text_mapping(slide, item, report_fields, workbench)
            _apply_plot_image(slide, image_path, MSO_SHAPE_TYPE)
            written += 1

    presentation.save(str(output))
    return {
        "template_path": str(template),
        "output_path": str(output),
        "slides_written": written,
        "items_exported": written,
    }
