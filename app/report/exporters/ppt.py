from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from struct import unpack

from app.report.plotting_config import PLOTTING_TEMPLATE_TEXT_MARKERS
from app.report.plotting_service import plotting_item_display_name, plotting_item_text, rendered_plot_images


class PptExportError(RuntimeError):
    pass


EMU_PER_INCH = 914400


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
    text = "\n".join(str(line) for line in list(lines or []))
    text_frame = shape.text_frame
    paragraphs = list(text_frame.paragraphs)
    if not paragraphs:
        paragraph = text_frame.add_paragraph()
        paragraph.text = text
        return
    paragraph = paragraphs[0]
    runs = list(paragraph.runs)
    if runs:
        runs[0].text = text
        for run in runs[1:]:
            run.text = ""
    else:
        paragraph.text = text
    for extra in paragraphs[1:]:
        extra_runs = list(extra.runs)
        if extra_runs:
            for run in extra_runs:
                run.text = ""
        else:
            extra.text = ""


def _duplicate_template_slide(presentation, source_slide):
    slide = presentation.slides.add_slide(source_slide.slide_layout)
    sp_tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        sp_tree.remove(shape.element)
    for shape in list(source_slide.shapes):
        sp_tree.insert_element_before(deepcopy(shape.element), "p:extLst")
    return slide


def _shape_size_inches(shape):
    return (
        float(getattr(shape, "width", 0) or 0) / EMU_PER_INCH,
        float(getattr(shape, "height", 0) or 0) / EMU_PER_INCH,
    )


def _png_size(image_path):
    try:
        with open(image_path, "rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
        return unpack(">II", header[16:24])
    return None


def _fit_rect_to_placeholder(image_path, left, top, width, height):
    image_size = _png_size(image_path)
    if not image_size:
        return left, top, width, height
    image_width, image_height = image_size
    if image_width <= 0 or image_height <= 0 or width <= 0 or height <= 0:
        return left, top, width, height

    placeholder_ratio = float(width) / float(height)
    image_ratio = float(image_width) / float(image_height)
    if image_ratio >= placeholder_ratio:
        fitted_width = width
        fitted_height = int(round(float(width) / image_ratio))
    else:
        fitted_height = height
        fitted_width = int(round(float(height) * image_ratio))
    fitted_left = int(round(float(left) + (float(width) - float(fitted_width)) / 2.0))
    fitted_top = int(round(float(top) + (float(height) - float(fitted_height)) / 2.0))
    return fitted_left, fitted_top, fitted_width, fitted_height


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
    left = plot_shape.left
    top = plot_shape.top
    width = plot_shape.width
    height = plot_shape.height
    pic_left, pic_top, pic_width, pic_height = _fit_rect_to_placeholder(image_path, left, top, width, height)
    slide.shapes.add_picture(str(image_path), pic_left, pic_top, width=pic_width, height=pic_height)
    if getattr(plot_shape, "has_text_frame", False):
        _set_shape_lines(plot_shape, [""])


def _notify_progress(progress_callback, current, total, message):
    if callable(progress_callback):
        progress_callback(int(current), int(total), str(message or ""))


def export_plotting_report_to_ppt(workbench, items, report_fields, output_path, template_path, progress_callback=None):
    Presentation, MSO_SHAPE_TYPE = _load_presentation_api()
    template = Path(str(template_path or "")).expanduser().resolve()
    if not template.exists():
        raise PptExportError(f"PPT template not found: {template}")

    included_items = [dict(item) for item in list(items or []) if bool(item.get("included", True))]
    if not included_items:
        raise PptExportError("No included plots to export.")

    total_steps = max(1, len(included_items) * 2 + 3)
    step = 0
    _notify_progress(progress_callback, step, total_steps, "PPT 템플릿을 여는 중...")

    presentation = Presentation(str(template))
    if not presentation.slides:
        raise PptExportError("Template has no slides.")
    template_slide = presentation.slides[0]
    plot_shape = _find_marker_shape(template_slide, PLOTTING_TEMPLATE_TEXT_MARKERS["plot_box"])
    if plot_shape is None:
        raise PptExportError("Template marker not found: Plot here")
    plot_size_inches = _shape_size_inches(plot_shape)
    step += 1
    _notify_progress(progress_callback, step, total_steps, "템플릿 매핑을 확인하는 중...")

    output = Path(str(output_path)).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    def _render_progress(rendered_count, render_total, item):
        nonlocal step
        step = min(total_steps - 2, 1 + int(rendered_count))
        label = plotting_item_display_name(item)
        _notify_progress(progress_callback, step, total_steps, f"그래프 렌더링 중... {label}")

    with rendered_plot_images(
        workbench,
        included_items,
        target_size_inches=plot_size_inches,
        progress_callback=_render_progress,
    ) as rendered_items:
        if not rendered_items:
            raise PptExportError("No rendered plots available for export.")
        slides = [template_slide]
        for _ in rendered_items[1:]:
            slides.append(_duplicate_template_slide(presentation, template_slide))

        for index, (slide, (item, image_path)) in enumerate(zip(slides, rendered_items), start=1):
            _apply_text_mapping(slide, item, report_fields, workbench)
            _apply_plot_image(slide, image_path, MSO_SHAPE_TYPE)
            written += 1
            step = min(total_steps - 1, 1 + len(rendered_items) + index)
            _notify_progress(
                progress_callback,
                step,
                total_steps,
                f"PPT 슬라이드 작성 중... {plotting_item_display_name(item)}",
            )

    _notify_progress(progress_callback, total_steps - 1, total_steps, "PPT 파일을 저장하는 중...")
    presentation.save(str(output))
    _notify_progress(progress_callback, total_steps, total_steps, "PPT export 완료")
    return {
        "template_path": str(template),
        "output_path": str(output),
        "slides_written": written,
        "items_exported": written,
    }
