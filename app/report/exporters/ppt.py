from __future__ import annotations

from pathlib import Path

from app.report.plotting_config import GRAPH_LAYOUT
from app.report.plotting_service import format_common_report_text, plotting_item_display_name, plotting_item_text, rendered_plot_images


class PptExportError(RuntimeError):
    pass


def _load_presentation_api():
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError as exc:
        raise PptExportError("python-pptx is required for PPT export. Install python-pptx and retry.") from exc
    return Presentation, Inches, Pt


def _clear_text_frame(shape):
    if not getattr(shape, "has_text_frame", False):
        return
    shape.text_frame.clear()


def _set_textbox_text(slide, box, text, *, font_size_pt, bold=False):
    left, top, width, height = box
    shape = slide.shapes.add_textbox(left, top, width, height)
    text_frame = shape.text_frame
    text_frame.word_wrap = True
    text_frame.clear()
    paragraph = text_frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = str(text or "").strip()
    run.font.size = font_size_pt
    run.font.bold = bool(bold)
    return shape


def export_plotting_report_to_ppt(workbench, items, report_fields, output_path, template_path):
    Presentation, Inches, Pt = _load_presentation_api()
    template = Path(str(template_path or "")).expanduser().resolve()
    if not template.exists():
        raise PptExportError(f"PPT template not found: {template}")

    presentation = Presentation(str(template))
    blank_layout = None
    for layout in presentation.slide_layouts:
        if not getattr(layout, "placeholders", None):
            blank_layout = layout
            break
    if blank_layout is None:
        blank_layout = presentation.slide_layouts[len(presentation.slide_layouts) - 1]

    output = Path(str(output_path)).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    common_text = format_common_report_text(report_fields)
    written = 0

    with rendered_plot_images(workbench, items) as rendered_items:
        for item, image_path in rendered_items:
            slide = presentation.slides.add_slide(blank_layout)
            title = plotting_item_display_name(item)
            _set_textbox_text(slide, tuple(Inches(v) for v in GRAPH_LAYOUT["title_box"]), title, font_size_pt=Pt(18), bold=True)
            _set_textbox_text(slide, tuple(Inches(v) for v in GRAPH_LAYOUT["common_box"]), common_text, font_size_pt=Pt(10), bold=False)
            left, top, width, height = [Inches(v) for v in GRAPH_LAYOUT["graph_box"]]
            slide.shapes.add_picture(str(image_path), left, top, width=width, height=height)
            _set_textbox_text(
                slide,
                tuple(Inches(v) for v in GRAPH_LAYOUT["injury_box"]),
                plotting_item_text(item),
                font_size_pt=Pt(10),
                bold=False,
            )
            written += 1

    presentation.save(str(output))
    return {
        "template_path": str(template),
        "output_path": str(output),
        "slides_written": written,
        "items_exported": written,
    }
