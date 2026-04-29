from __future__ import annotations

import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

from app.core.utils.formatting import fmt_metric_at, fmt_metric_range, fmt_time_ms, fmt_value
from app.report.formatters import (
    calculation_context_root,
    canonical_graphs_root,
    canonical_metric_detail,
    canonical_metrics_root,
    context_dummy_profile,
    context_input_channel,
    context_parameter,
)
from app.report.plotting_config import (
    COMMON_REPORT_FIELD_ORDER,
    PLOTTING_CACHE_KEY,
    PLOTTING_GRAPH_TEXT_RULES,
    PLOTTING_OUTPUT_SUFFIX,
    PLOTTING_SAVE_SUFFIX,
    PLOTTING_TEMPLATE_PATH,
)
from app.services.state.injury_result_store import get_section_payload, get_slot_payload


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
    structured = dict(slot_payload.get("structured_metrics") or {})
    context = {
        "payload": slot_payload,
        "channels": dict(slot_payload.get("channels") or {}),
        "report_values": dict(slot_payload.get("report_values") or {}),
        "metric_extrema": dict(slot_payload.get("metric_extrema") or {}),
        "structured_metrics": structured,
        "canonical_metrics": dict(slot_payload.get("canonical_metrics") or {}),
        "calculation_context": dict(slot_payload.get("calculation_context") or {}),
        "canonical_graphs": dict(slot_payload.get("canonical_graphs") or {}),
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


def _canonical_metric_detail(context, *path):
    return canonical_metric_detail(context, *path)


def _canonical_injury_detail(context, detail_key):
    key = str(detail_key or "").strip()
    if not key:
        return {}
    if key.endswith("_detail"):
        key = key[:-7]
    return _canonical_metric_detail(context, "injury", key)


def _context_input_channel(context, *path):
    return context_input_channel(context, *path)


def _context_parameter(context, key_name, default=None):
    return context_parameter(context, key_name, default)


def _context_dummy_profile(context, default="-"):
    return context_dummy_profile(context, default)


def _axis_extrema_lines(axis_key, unit, context, *, value_indent=""):
    channels = dict(context.get("channels") or {})
    metric_extrema = dict(context.get("metric_extrema") or {})
    channel_name = _context_input_channel(context, str(axis_key or "").lower()) or channels.get(axis_key) or ""
    canonical_detail = _canonical_metric_detail(context, "acc", str(axis_key or "").lower())
    if canonical_detail:
        channel_name = canonical_detail.get("channel") or channel_name
        display_name = canonical_detail.get("display_name") or f"ACC {str(axis_key or '').upper()}"
        max_detail = dict(canonical_detail.get("max") or {})
        min_detail = dict(canonical_detail.get("min") or {})
        unit = canonical_detail.get("unit") or unit
        return [
            _axis_display_name(str(display_name).split()[-1] if display_name.startswith("ACC ") else axis_key, channel_name),
            f"{value_indent}Max : {fmt_value(max_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(max_detail.get('time_s'))}",
            f"{value_indent}Min : {fmt_value(min_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(min_detail.get('time_s'))}",
        ]
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
        f"{value_indent}Max : {fmt_value((detail or {}).get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('max_time_s'))}",
        f"{value_indent}Min : {fmt_value((detail or {}).get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('min_time_s'))}",
    ]


def _resultant_extrema_lines(resultant_label, resultant_key, unit, context, rule=None):
    metric_extrema = dict(context.get("metric_extrema") or {})
    report_values = dict(context.get("report_values") or {})
    payload = dict(context.get("payload") or {})
    rule = dict(rule or {})
    multiline_value = bool(rule.get("resultant_multiline_value"))
    value_indent = str(rule.get("resultant_value_indent") or "")
    blank_between = bool(rule.get("resultant_blank_between", False))
    max_prefix = f"{resultant_label} MAX"
    min_prefix = f"{resultant_label} MIN"
    canonical_detail = _canonical_metric_detail(context, "acc", "resultant")
    def _render_value_lines(prefix, value, time_s):
        if multiline_value:
            return [
                prefix,
                f"{value_indent}: {fmt_value(value, unit, unit_style='suffix')} at {fmt_time_ms(time_s)}",
            ]
        return [f"{prefix}: ", f"{fmt_value(value, unit, unit_style='suffix')} at {fmt_time_ms(time_s)}"]
    if canonical_detail:
        max_detail = dict(canonical_detail.get("max") or {})
        min_detail = dict(canonical_detail.get("min") or {})
        unit = canonical_detail.get("unit") or unit
        lines = [*_render_value_lines(max_prefix, max_detail.get("value"), max_detail.get("time_s"))]
        if blank_between:
            lines.append("")
        lines.extend(_render_value_lines(min_prefix, min_detail.get("value"), min_detail.get("time_s")))
        return lines
    detail = dict(metric_extrema.get(resultant_key) or {})
    if not detail:
        detail = {
            "max_value": report_values.get(rule.get("resultant_max_value_key")),
            "max_time_s": report_values.get(rule.get("resultant_max_time_key")),
            "min_value": report_values.get(rule.get("resultant_min_value_key")),
            "min_time_s": report_values.get(rule.get("resultant_min_time_key")),
        }
    if detail.get("max_time_s") is None:
        detail["max_time_s"] = payload.get(rule.get("resultant_max_time_key"))
    if detail.get("min_time_s") is None:
        detail["min_time_s"] = payload.get(rule.get("resultant_min_time_key"))
    if detail.get("max_value") is None:
        detail["max_value"] = payload.get(rule.get("resultant_max_value_key"))
    if detail.get("min_value") is None:
        detail["min_value"] = payload.get(rule.get("resultant_min_value_key"))
    lines = [*_render_value_lines(max_prefix, detail.get("max_value"), detail.get("max_time_s"))]
    if blank_between:
        lines.append("")
    lines.extend(_render_value_lines(min_prefix, detail.get("min_value"), detail.get("min_time_s")))
    return lines


def _neck_axis_display_name(axis_key, context):
    canonical_group = "force" if str(axis_key).startswith("F") else "moment"
    canonical_detail = _canonical_metric_detail(context, canonical_group, axis_key[-1].lower())
    if canonical_detail:
        channel = _context_input_channel(context, axis_key) or str(canonical_detail.get("channel") or "").strip() or "-"
        return f"{axis_key} - {channel}"
    structured = dict(context.get("structured_metrics") or {})
    display_names = dict(structured.get("display_channel_names") or {})
    return str(display_names.get(axis_key) or f"{axis_key} - -")


def _neck_axis_unit(axis_key, context):
    canonical_group = "force" if str(axis_key).startswith("F") else "moment"
    canonical_detail = _canonical_metric_detail(context, canonical_group, axis_key[-1].lower())
    if canonical_detail:
        return str(canonical_detail.get("unit") or ("N" if str(axis_key).startswith("F") else "Nm"))
    structured = dict(context.get("structured_metrics") or {})
    display_units = dict(structured.get("display_units") or {})
    return str(display_units.get(axis_key) or ("N" if str(axis_key).startswith("F") else "Nm"))


def _neck_force_extrema_lines(axis_key, context):
    canonical_detail = _canonical_metric_detail(context, "force", axis_key[-1].lower())
    detail = {}
    if canonical_detail:
        detail = {
            "max_value": dict(canonical_detail.get("max") or {}).get("value"),
            "max_time_s": dict(canonical_detail.get("max") or {}).get("time_s"),
            "min_value": dict(canonical_detail.get("min") or {}).get("value"),
            "min_time_s": dict(canonical_detail.get("min") or {}).get("time_s"),
        }
    else:
        metric_extrema = dict(context.get("metric_extrema") or {})
        detail = dict(metric_extrema.get(f"display_series.{axis_key}") or {})
    label = _neck_axis_display_name(axis_key, context)
    unit = _neck_axis_unit(axis_key, context)
    max_label = "Max"
    min_label = "Min"
    if axis_key == "Fx":
        max_label = "Max(Rear Shear)"
        min_label = "Min(Forward Shear)"
    elif axis_key == "Fz":
        max_label = "Max(Tension)"
        min_label = "Min(Compression)"
    if axis_key == "Fy":
        return [
            label,
            f"  {max_label} : {fmt_value((detail or {}).get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('max_time_s'))}",
            f"  {min_label} : {fmt_value((detail or {}).get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('min_time_s'))}",
        ]
    return [
        label,
        f"  {max_label}",
        f"    : {fmt_value((detail or {}).get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('max_time_s'))}",
        f"  {min_label}",
        f"    : {fmt_value((detail or {}).get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('min_time_s'))}",
    ]


def _neck_moment_extrema_lines(axis_key, context):
    canonical_detail = _canonical_metric_detail(context, "moment", axis_key[-1].lower())
    detail = {}
    if canonical_detail:
        detail = {
            "max_value": dict(canonical_detail.get("max") or {}).get("value"),
            "max_time_s": dict(canonical_detail.get("max") or {}).get("time_s"),
            "min_value": dict(canonical_detail.get("min") or {}).get("value"),
            "min_time_s": dict(canonical_detail.get("min") or {}).get("time_s"),
        }
    else:
        metric_extrema = dict(context.get("metric_extrema") or {})
        detail = dict(metric_extrema.get(f"display_series.{axis_key}") or {})
    label = _neck_axis_display_name(axis_key, context)
    unit = _neck_axis_unit(axis_key, context)
    max_label = "Max"
    min_label = "Min"
    if axis_key == "My":
        max_label = "MAX(Flexion)"
        min_label = "MIN(Extension)"
        return [
            label,
            f"  {max_label}",
            f"    : {fmt_value((detail or {}).get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('max_time_s'))}",
            f"  {min_label}",
            f"    : {fmt_value((detail or {}).get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('min_time_s'))}",
        ]
    return [
        label,
        f"  {max_label}: {fmt_value((detail or {}).get('max_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('max_time_s'))}",
        f"  {min_label}: {fmt_value((detail or {}).get('min_value'), unit, unit_style='suffix')} at {fmt_time_ms((detail or {}).get('min_time_s'))}",
    ]


def _neck_mocy_summary_lines(context):
    structured = dict(context.get("structured_metrics") or {})
    criteria = dict(structured.get("criteria") or {})
    canonical_mocy = _canonical_metric_detail(context, "moment", "mocy")
    dummy_family = _context_dummy_profile(context, criteria.get("dummy_family") or criteria.get("criterion_key") or "-")
    input_moment = str(_context_parameter(context, "input_moment", canonical_mocy.get("input") or criteria.get("input_moment") or "My") or "My")
    moc_d = _context_parameter(context, "moc_d_m", canonical_mocy.get("lever_arm_m", criteria.get("moc_d", 0.0)))
    try:
        moc_d_value = float(moc_d)
    except Exception:
        moc_d_value = 0.0
    moc_applied_flag = _context_parameter(context, "moc_applied", canonical_mocy.get("applied", criteria.get("moc_applied")))
    moc_applied = "Yes" if moc_applied_flag else "No"
    peak_flexion_detail = dict(canonical_mocy.get("peak_flexion") or {})
    peak_extension_detail = dict(canonical_mocy.get("peak_extension") or {})
    peak_flexion = peak_flexion_detail.get("value", structured.get("peak_flexion_my"))
    peak_flexion_time = peak_flexion_detail.get("time_s", structured.get("peak_flexion_time"))
    peak_extension = peak_extension_detail.get("value", structured.get("peak_extension_my"))
    peak_extension_time = peak_extension_detail.get("time_s", structured.get("peak_extension_time"))
    return [
        f"Dummy Family: {dummy_family}",
        f"Moment Input: {input_moment}",
        f"Lever arm D: {moc_d_value:.6f} m",
        f"MOC 적용: {moc_applied}",
        "",
        "- Injuries -",
        "Peak Flexion MOCy",
        f"  : {fmt_value(peak_flexion, 'Nm', unit_style='suffix')} at {fmt_time_ms(peak_flexion_time)}",
        "",
        "Peak Extension MOCy",
        f"  : {fmt_value(peak_extension, 'Nm', unit_style='suffix')} at {fmt_time_ms(peak_extension_time)}",
    ]


def _neck_nij_components_summary_lines(context):
    structured = dict(context.get("structured_metrics") or {})
    canonical_injury = _canonical_metric_detail(context, "injury")
    nte = dict(canonical_injury.get("nte") or {})
    ntf = dict(canonical_injury.get("ntf") or {})
    nce = dict(canonical_injury.get("nce") or {})
    ncf = dict(canonical_injury.get("ncf") or {})
    nij = dict(canonical_injury.get("nij") or {})
    overall = dict(nij.get("overall") or {})
    return [
        "- Injuries –",
        "",
        fmt_metric_at("NTE", nte.get("value", structured.get("peak_nte")), time_s=nte.get("time_s", structured.get("peak_nte_time"))),
        fmt_metric_at("NTF", ntf.get("value", structured.get("peak_ntf")), time_s=ntf.get("time_s", structured.get("peak_ntf_time"))),
        fmt_metric_at("NCE", nce.get("value", structured.get("peak_nce")), time_s=nce.get("time_s", structured.get("peak_nce_time"))),
        fmt_metric_at("NCF", ncf.get("value", structured.get("peak_ncf")), time_s=ncf.get("time_s", structured.get("peak_ncf_time"))),
        "",
        fmt_metric_at("Overall Nij", overall.get("value", structured.get("overall_nij")), time_s=overall.get("time_s", structured.get("overall_nij_time"))),
        f"Dominant Mode: {nij.get('dominant_mode') or structured.get('dominant_mode') or '-'}",
    ]


def _neck_nij_overall_summary_lines(context):
    structured = dict(context.get("structured_metrics") or {})
    canonical_injury = _canonical_metric_detail(context, "injury")
    nij = dict(canonical_injury.get("nij") or {})
    overall = dict(nij.get("overall") or {})
    return [
        "- Injuries -",
        "",
        fmt_metric_at("Overall Nij", overall.get("value", structured.get("overall_nij")), time_s=overall.get("time_s", structured.get("overall_nij_time"))),
        f"Dominant Mode: {nij.get('dominant_mode') or structured.get('dominant_mode') or '-'}",
    ]


def _chest_displacement_summary_lines(context):
    canonical_disp = _canonical_metric_detail(context, "displacement")
    if canonical_disp:
        detail = {
            "max_value": dict(canonical_disp.get("max") or {}).get("value"),
            "max_time_s": dict(canonical_disp.get("max") or {}).get("time_s"),
            "min_value": dict(canonical_disp.get("min") or {}).get("value"),
            "min_time_s": dict(canonical_disp.get("min") or {}).get("time_s"),
        }
        peak_detail = dict(canonical_disp.get("peak") or {})
    else:
        metric_extrema = dict(context.get("metric_extrema") or {})
        detail = dict(metric_extrema.get("displacement_mm") or {})
        peak_detail = dict((context.get("details") or {}).get("displacement_peak") or {})
    return [
        "- Injuries -",
        "Displacement Max",
        f"  : {fmt_value(detail.get('max_value'), 'mm', unit_style='suffix')} at {fmt_time_ms(detail.get('max_time_s'))}",
        "Displacement Min",
        f"  : {fmt_value(detail.get('min_value'), 'mm', unit_style='suffix')} at {fmt_time_ms(detail.get('min_time_s'))}",
        "",
        "Displacement Peak",
        f"  : {fmt_value(peak_detail.get('value'), 'mm', unit_style='suffix')} at {fmt_time_ms(peak_detail.get('time_s'))}",
    ]


def _chest_vc_summary_lines(context):
    canonical_vc = _canonical_metric_detail(context, "vc")
    if canonical_vc:
        sae = {
            "max_value": dict((canonical_vc.get("sae_j1727_cfc600") or {}).get("max") or {}).get("value"),
            "max_time_s": dict((canonical_vc.get("sae_j1727_cfc600") or {}).get("max") or {}).get("time_s"),
            "min_value": dict((canonical_vc.get("sae_j1727_cfc600") or {}).get("min") or {}).get("value"),
            "min_time_s": dict((canonical_vc.get("sae_j1727_cfc600") or {}).get("min") or {}).get("time_s"),
        }
        ece = {
            "max_value": dict((canonical_vc.get("ece94_cfc180") or {}).get("max") or {}).get("value"),
            "max_time_s": dict((canonical_vc.get("ece94_cfc180") or {}).get("max") or {}).get("time_s"),
            "min_value": dict((canonical_vc.get("ece94_cfc180") or {}).get("min") or {}).get("value"),
            "min_time_s": dict((canonical_vc.get("ece94_cfc180") or {}).get("min") or {}).get("time_s"),
        }
    else:
        metric_extrema = dict(context.get("metric_extrema") or {})
        sae = dict(metric_extrema.get("vc_sae") or {})
        ece = dict(metric_extrema.get("vc_ece") or {})
    return [
        "- Injuries -",
        "V*C SAE J1727_CFC600",
        f"Max: {fmt_value(sae.get('max_value'), 'm/s', unit_style='suffix')} at {fmt_time_ms(sae.get('max_time_s'))}",
        f"Min: {fmt_value(sae.get('min_value'), 'm/s', unit_style='suffix')} at {fmt_time_ms(sae.get('min_time_s'))}",
        "",
        "V*C ECE94_CFC180",
        f"Max: {fmt_value(ece.get('max_value'), 'm/s', unit_style='suffix')} at {fmt_time_ms(ece.get('max_time_s'))}",
        f"Min: {fmt_value(ece.get('min_value'), 'm/s', unit_style='suffix')} at {fmt_time_ms(ece.get('min_time_s'))}",
    ]


def _femur_combined_summary_lines(context):
    left_force = _canonical_metric_detail(context, "force", "left")
    right_force = _canonical_metric_detail(context, "force", "right")
    injury = _canonical_metric_detail(context, "injury")
    left_peak = dict(injury.get("left_peak") or {})
    right_peak = dict(injury.get("right_peak") or {})
    left_channel = _context_input_channel(context, "left") or str(left_force.get("channel") or "").strip() or "-"
    right_channel = _context_input_channel(context, "right") or str(right_force.get("channel") or "").strip() or "-"
    left_max = dict(left_force.get("max") or {})
    left_min = dict(left_force.get("min") or {})
    right_max = dict(right_force.get("max") or {})
    right_min = dict(right_force.get("min") or {})
    return [
        "FEMUR FORCE LEFT Max",
        f"  - {left_channel}",
        f"    : {fmt_value(left_max.get('value'), 'N', unit_style='suffix')} at {fmt_time_ms(left_max.get('time_s'))}",
        "FEMUR FORCE LEFT Min",
        f"  - {left_channel}",
        f"    : {fmt_value(left_min.get('value'), 'N', unit_style='suffix')} at {fmt_time_ms(left_min.get('time_s'))}",
        "",
        "FEMUR FORCE RIGHT Max",
        f"  - {right_channel}",
        f"    : {fmt_value(right_max.get('value'), 'N', unit_style='suffix')} at {fmt_time_ms(right_max.get('time_s'))}",
        "FEMUR FORCE RIGHT Min",
        f"  - {right_channel}",
        f"    : {fmt_value(right_min.get('value'), 'N', unit_style='suffix')} at {fmt_time_ms(right_min.get('time_s'))}",
        "",
        "- Injuries -",
        "Left Peak Axial Force",
        f"  : {fmt_value(left_peak.get('value'), 'N', unit_style='suffix')} at {fmt_time_ms(left_peak.get('time_s'))}",
        "Right Peak Axial Force",
        f"  : {fmt_value(right_peak.get('value'), 'N', unit_style='suffix')} at {fmt_time_ms(right_peak.get('time_s'))}",
    ]


def _knee_combined_summary_lines(context):
    left_disp = _canonical_metric_detail(context, "displacement", "left")
    right_disp = _canonical_metric_detail(context, "displacement", "right")
    left_peak = dict(left_disp.get("peak") or {})
    right_peak = dict(right_disp.get("peak") or {})
    return [
        "Left Knee Slider Peak",
        f"  : {fmt_value(left_peak.get('value'), 'mm', unit_style='suffix')} at {fmt_time_ms(left_peak.get('time_s'))}",
        "",
        "Right Knee Slider Peak",
        f"  : {fmt_value(right_peak.get('value'), 'mm', unit_style='suffix')} at {fmt_time_ms(right_peak.get('time_s'))}",
    ]


def _iliac_force_summary_lines(context):
    left_fx = _canonical_metric_detail(context, "force", "left_fx")
    right_fx = _canonical_metric_detail(context, "force", "right_fx")

    def _extrema_block(title, detail, unit):
        detail = dict(detail or {})
        max_detail = dict(detail.get("max") or {})
        min_detail = dict(detail.get("min") or {})
        return [
            title,
            f"  Max : {fmt_value(max_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(max_detail.get('time_s'))}",
            f"  Min : {fmt_value(min_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(min_detail.get('time_s'))}",
        ]

    lines = ["ILIAC - LEFT"]
    lines.extend(_extrema_block(f"Fx - {str(left_fx.get('channel') or '-').strip() or '-'}", left_fx, "N"))
    lines.append("")
    lines.append("ILIAC - RIGHT")
    lines.extend(_extrema_block(f"Fx - {str(right_fx.get('channel') or '-').strip() or '-'}", right_fx, "N"))
    return lines


def _iliac_moment_summary_lines(context):
    left_my = _canonical_metric_detail(context, "moment", "left_my")
    right_my = _canonical_metric_detail(context, "moment", "right_my")

    def _extrema_block(title, detail, unit):
        detail = dict(detail or {})
        max_detail = dict(detail.get("max") or {})
        min_detail = dict(detail.get("min") or {})
        return [
            title,
            f"  Max : {fmt_value(max_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(max_detail.get('time_s'))}",
            f"  Min : {fmt_value(min_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(min_detail.get('time_s'))}",
        ]

    lines = ["ILIAC - LEFT"]
    lines.extend(_extrema_block(f"My - {str(left_my.get('channel') or '-').strip() or '-'}", left_my, "Nm"))
    lines.append("")
    lines.append("ILIAC - RIGHT")
    lines.extend(_extrema_block(f"My - {str(right_my.get('channel') or '-').strip() or '-'}", right_my, "Nm"))
    return lines


def _iliac_crossplot_summary_lines(context):
    left_fx = _canonical_metric_detail(context, "force", "left_fx")
    right_fx = _canonical_metric_detail(context, "force", "right_fx")
    left_my = _canonical_metric_detail(context, "moment", "left_my")
    right_my = _canonical_metric_detail(context, "moment", "right_my")

    def _extrema_block(title, detail, unit):
        detail = dict(detail or {})
        max_detail = dict(detail.get("max") or {})
        min_detail = dict(detail.get("min") or {})
        return [
            title,
            f"  Max : {fmt_value(max_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(max_detail.get('time_s'))}",
            f"  Min : {fmt_value(min_detail.get('value'), unit, unit_style='suffix')} at {fmt_time_ms(min_detail.get('time_s'))}",
        ]

    lines = ["ILIAC - LEFT"]
    lines.extend(_extrema_block(f"Fx - {str(left_fx.get('channel') or '-').strip() or '-'}", left_fx, "N"))
    lines.append("")
    lines.extend(_extrema_block(f"My - {str(left_my.get('channel') or '-').strip() or '-'}", left_my, "Nm"))
    lines.append("")
    lines.append("ILIAC - RIGHT")
    lines.extend(_extrema_block(f"Fx - {str(right_fx.get('channel') or '-').strip() or '-'}", right_fx, "N"))
    lines.append("")
    lines.extend(_extrema_block(f"My - {str(right_my.get('channel') or '-').strip() or '-'}", right_my, "Nm"))
    return lines


def _injury_line_from_rule(line_rule, context):
    report_values = dict(context.get("report_values") or {})
    details = dict(context.get("details") or {})
    kind = str((line_rule or {}).get("type") or "").strip().lower()
    label = str((line_rule or {}).get("label") or "").strip()
    unit = str((line_rule or {}).get("unit") or "")
    def _value_from_rule(key_name):
        return report_values.get(key_name) if report_values.get(key_name) is not None else details.get(key_name)
    if kind == "range":
        if line_rule.get("detail_key"):
            detail = dict(details.get(line_rule.get("detail_key")) or {})
            if not detail:
                detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
            return fmt_metric_range(
                label,
                detail.get("value"),
                unit=unit,
                start_s=detail.get("start_time_s"),
                end_s=detail.get("end_time_s"),
            )
        return fmt_metric_range(
            label,
            _value_from_rule(line_rule.get("value_key")),
            unit=unit,
            start_s=details.get(line_rule.get("start_key")),
            end_s=details.get(line_rule.get("end_key")),
        )
    if kind == "at":
        if line_rule.get("detail_key"):
            detail = dict(details.get(line_rule.get("detail_key")) or {})
            if not detail:
                detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
            return fmt_metric_at(label, detail.get("value"), unit=unit, time_s=detail.get("time_s"))
        return fmt_metric_at(
            label,
            _value_from_rule(line_rule.get("value_key")),
            unit=unit,
            time_s=details.get(line_rule.get("time_key")),
        )
    if kind in {"detail_range", "range_detail"}:
        detail = dict(details.get(line_rule.get("detail_key")) or {})
        if not detail:
            detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
        return fmt_metric_range(label, detail.get("value"), unit=unit, start_s=detail.get("start_time_s"), end_s=detail.get("end_time_s"))
    if kind == "detail_at":
        detail = dict(details.get(line_rule.get("detail_key")) or {})
        if not detail:
            detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
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
            f"[{slot} - FMVSS Head 80g / 3ms Limit]",
            f"  Result : {status} ({duration_text})",
        ])
    return "-"


def _multiline_injury_block_from_rule(line_rule, context):
    report_values = dict(context.get("report_values") or {})
    details = dict(context.get("details") or {})
    kind = str((line_rule or {}).get("type") or "").strip().lower()
    label = str((line_rule or {}).get("label") or "").strip()
    unit = str((line_rule or {}).get("unit") or "")

    def _value_from_rule(key_name):
        return report_values.get(key_name) if report_values.get(key_name) is not None else details.get(key_name)

    if kind == "range":
        if line_rule.get("detail_key"):
            detail = dict(details.get(line_rule.get("detail_key")) or {})
            if not detail:
                detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
            value_text = fmt_metric_range(
                "",
                detail.get("value"),
                unit=unit,
                start_s=detail.get("start_time_s"),
                end_s=detail.get("end_time_s"),
            ).lstrip(": ").strip()
            return f"{label}\n  : {value_text}"
        value_text = fmt_metric_range(
            "",
            _value_from_rule(line_rule.get("value_key")),
            unit=unit,
            start_s=details.get(line_rule.get("start_key")),
            end_s=details.get(line_rule.get("end_key")),
        ).lstrip(": ").strip()
        return f"{label}\n  : {value_text}"
    if kind == "at":
        if line_rule.get("detail_key"):
            detail = dict(details.get(line_rule.get("detail_key")) or {})
            if not detail:
                detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
            value_text = fmt_metric_at("", detail.get("value"), unit=unit, time_s=detail.get("time_s")).lstrip(": ").strip()
            return f"{label}\n  : {value_text}"
        value_text = fmt_metric_at(
            "",
            _value_from_rule(line_rule.get("value_key")),
            unit=unit,
            time_s=details.get(line_rule.get("time_key")),
        ).lstrip(": ").strip()
        return f"{label}\n  : {value_text}"
    if kind in {"detail_range", "range_detail"}:
        detail = dict(details.get(line_rule.get("detail_key")) or {})
        if not detail:
            detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
        value_text = fmt_metric_range("", detail.get("value"), unit=unit, start_s=detail.get("start_time_s"), end_s=detail.get("end_time_s")).lstrip(": ").strip()
        return f"{label}\n  : {value_text}"
    if kind == "detail_at":
        detail = dict(details.get(line_rule.get("detail_key")) or {})
        if not detail:
            detail = _canonical_injury_detail(context, line_rule.get("detail_key"))
        value_text = fmt_metric_at("", detail.get("value"), unit=unit, time_s=detail.get("time_s")).lstrip(": ").strip()
        return f"{label}\n  : {value_text}"
    if kind == "fmvss_head_80g":
        return _injury_line_from_rule(line_rule, context)
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
    if template in {"acc_axes", "acc_axes_then_resultant", "acc_axes_then_injuries"}:
        axis_keys = tuple(rule.get("axis_keys") or ())
        for index, axis_key in enumerate(axis_keys):
            if index > 0:
                lines.append("")
            lines.extend(_axis_extrema_lines(axis_key, rule.get("unit") or "g", context, value_indent=str(rule.get("axis_value_indent") or "")))
        if template in {"acc_axes_then_resultant", "acc_axes_then_injuries"}:
            lines.append("")
            lines.extend(_resultant_extrema_lines(rule.get("resultant_label") or "Resultant", rule.get("resultant_key") or "resultant", rule.get("unit") or "g", context, rule))
        if template == "acc_axes_then_injuries":
            lines.append("- Injuries -")
            for line_rule in tuple(rule.get("injury_lines") or ()):
                if rule.get("injury_multiline_value"):
                    lines.append(_multiline_injury_block_from_rule(line_rule, context))
                else:
                    lines.append(_injury_line_from_rule(line_rule, context))
    elif template == "acc_resultant_with_injuries":
        lines.extend(_resultant_extrema_lines(rule.get("resultant_label") or "Resultant", rule.get("resultant_key") or "resultant", rule.get("unit") or "g", context, rule))
        lines.append("- Injuries -")
        for line_rule in tuple(rule.get("injury_lines") or ()):
            lines.append(_injury_line_from_rule(line_rule, context))
    elif template == "head_resultant_injuries":
        lines.append("- Injuries  -")
        for index, line_rule in enumerate(tuple(rule.get("injury_lines") or ())):
            if index > 0:
                lines.append("")
            lines.append(_multiline_injury_block_from_rule(line_rule, context))
    elif template == "neck_force_axes":
        lines.append(str(rule.get("title") or "UPPER NECK FORCE"))
        for index, axis_key in enumerate(tuple(rule.get("axis_keys") or ())):
            lines.append("")
            lines.extend(_neck_force_extrema_lines(axis_key, context))
    elif template == "neck_moment_axes":
        lines.append(str(rule.get("title") or "UPPER NECK MOMENT"))
        for index, axis_key in enumerate(tuple(rule.get("axis_keys") or ())):
            lines.append("")
            lines.extend(_neck_moment_extrema_lines(axis_key, context))
    elif template == "neck_mocy_summary":
        lines.extend(_neck_mocy_summary_lines(context))
    elif template == "neck_nij_components_summary":
        lines.extend(_neck_nij_components_summary_lines(context))
    elif template == "neck_nij_overall_summary":
        lines.extend(_neck_nij_overall_summary_lines(context))
    elif template == "chest_displacement_summary":
        lines.extend(_chest_displacement_summary_lines(context))
    elif template == "chest_vc_summary":
        lines.extend(_chest_vc_summary_lines(context))
    elif template == "femur_combined_summary":
        lines.extend(_femur_combined_summary_lines(context))
    elif template == "knee_combined_summary":
        lines.extend(_knee_combined_summary_lines(context))
    elif template == "iliac_force_summary":
        lines.extend(_iliac_force_summary_lines(context))
    elif template == "iliac_moment_summary":
        lines.extend(_iliac_moment_summary_lines(context))
    elif template == "iliac_crossplot_summary":
        lines.extend(_iliac_crossplot_summary_lines(context))
    while lines and str(lines[-1] or "").strip() == "":
        lines.pop()
    text = "\n".join(line for line in lines if line is not None)
    return text or (str(item.get("summary_text") or "-").strip() or "-")


def _collect_page_plot_items(workbench, page_key, section_key):
    page = (getattr(workbench, "pages", {}) or {}).get(page_key)
    if page is None:
        return []
    if hasattr(page, "apply_shared_dummy_config"):
        try:
            page.apply_shared_dummy_config()
        except Exception:
            pass
    if hasattr(page, "_restore_saved_injury_results"):
        try:
            page._restore_saved_injury_results()
        except Exception:
            pass
    metadata = dict(getattr(workbench, "dataset_metadata", {}) or {})
    section_payload = get_section_payload(metadata, section_key)
    slots_payload = dict(section_payload.get("slots") or {})
    if not slots_payload:
        return []
    items = []
    for slot in [slot for slot in ("B1", "B2", "B3", "B4", "B5", "B6") if slot in slots_payload]:
        slot_payload = get_slot_payload(metadata, section_key, slot)
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
        previous_mode = str(previous.get("text_mode") or "auto").strip().lower()
        previous_custom = str(previous.get("custom_text") or "")
        previous_summary = str(previous.get("summary_text") or "").strip()
        stale_auto_copy = previous_mode == "custom" and previous_custom.strip() == previous_summary and previous_summary not in ("", "-")
        fresh["included"] = bool(previous.get("included", True))
        fresh["text_mode"] = "auto" if stale_auto_copy else str(previous.get("text_mode") or "auto")
        fresh["custom_text"] = "" if stale_auto_copy else previous_custom
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


def render_plot_image(workbench, item, output_path, target_size_inches=None):
    item = dict(item or {})
    page = (getattr(workbench, "pages", {}) or {}).get(item.get("page_key"))
    if page is None:
        raise RuntimeError(f"Plot page not found: {item.get('page_key')}")
    slot = str(item.get("slot") or "").strip()
    graph_key = str(item.get("graph_key") or "").strip()
    if not slot or not graph_key:
        raise RuntimeError("Invalid plot item.")
    previous_slot = page._active_slot() if hasattr(page, "_active_slot") else None
    original_size = tuple(float(v) for v in page.figure.get_size_inches())
    target_size = tuple(float(v) for v in target_size_inches or () if float(v) > 0.0)
    try:
        if len(target_size) == 2:
            page.figure.set_size_inches(target_size[0], target_size[1], forward=True)
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
        page.figure.savefig(output_path, dpi=180)
    finally:
        if len(original_size) == 2:
            page.figure.set_size_inches(original_size[0], original_size[1], forward=True)
        if previous_slot and hasattr(page, "active_dummy_var"):
            try:
                page.active_dummy_var.set(previous_slot)
            except Exception:
                pass
        canvas = getattr(page, "canvas", None)
        if canvas is not None and hasattr(canvas, "draw_idle"):
            try:
                canvas.draw_idle()
            except Exception:
                pass
    return str(output_path)


@contextmanager
def rendered_plot_images(workbench, items, target_size_inches=None, progress_callback=None):
    rendered = []
    with tempfile.TemporaryDirectory(prefix="crashoutput_plotting_") as tmpdir:
        temp_dir = Path(tmpdir)
        included_items = [dict(item) for item in list(items or []) if bool(item.get("included", True))]
        total = len(included_items)
        for index, item in enumerate(included_items, start=1):
            if not bool(item.get("included", True)):
                continue
            file_name = f"{index:03d}_{str(item.get('item_key') or 'plot').replace('|', '_')}.png"
            image_path = temp_dir / file_name
            render_plot_image(workbench, item, image_path, target_size_inches=target_size_inches)
            rendered.append((dict(item), image_path))
            if callable(progress_callback):
                progress_callback(index, total, item)
        yield rendered
