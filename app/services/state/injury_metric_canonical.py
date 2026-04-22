"""Canonical injury metric payload helpers.

This module normalizes section-specific computed results into a shared
`section + metric + axis/component` structure so formatters can stop depending
on legacy per-module field names over time.
"""

from __future__ import annotations


def _float_or_none(value):
    try:
        result = float(value)
    except Exception:
        return None
    return result if result == result else None


def _text(value, fallback=""):
    text = str(value or "").strip()
    return text or fallback


def _point(value=None, time_s=None, unit=""):
    return {
        "value": _float_or_none(value),
        "time_s": _float_or_none(time_s),
        "unit": _text(unit),
    }


def _range(value=None, start_time_s=None, end_time_s=None, unit=""):
    return {
        "value": _float_or_none(value),
        "start_time_s": _float_or_none(start_time_s),
        "end_time_s": _float_or_none(end_time_s),
        "unit": _text(unit),
    }


def _extrema(max_value=None, max_time_s=None, min_value=None, min_time_s=None, unit="", channel="", display_name=""):
    return {
        "channel": _text(channel),
        "display_name": _text(display_name),
        "unit": _text(unit),
        "max": _point(max_value, max_time_s, unit=unit),
        "min": _point(min_value, min_time_s, unit=unit),
    }


def _head_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    channels = dict(payload.get("channels") or {})
    unit = _text(payload.get("plot_unit") or payload.get("report_values", {}).get("plot_unit") or "g", "g")
    return {
        "acc": {
            "x": _extrema(
                metrics.get("head_x_max_value"),
                metrics.get("head_x_max_time_s"),
                metrics.get("head_x_min_value"),
                metrics.get("head_x_min_time_s"),
                unit=unit,
                channel=channels.get("x"),
                display_name="ACC X",
            ),
            "y": _extrema(
                metrics.get("head_y_max_value"),
                metrics.get("head_y_max_time_s"),
                metrics.get("head_y_min_value"),
                metrics.get("head_y_min_time_s"),
                unit=unit,
                channel=channels.get("y"),
                display_name="ACC Y",
            ),
            "z": _extrema(
                metrics.get("head_z_max_value"),
                metrics.get("head_z_max_time_s"),
                metrics.get("head_z_min_value"),
                metrics.get("head_z_min_time_s"),
                unit=unit,
                channel=channels.get("z"),
                display_name="ACC Z",
            ),
            "resultant": _extrema(
                metrics.get("head_resultant_max_value"),
                metrics.get("head_resultant_max_time_s"),
                metrics.get("head_resultant_min_value"),
                metrics.get("head_resultant_min_time_s"),
                unit=unit,
                channel=payload.get("resultant_channel"),
                display_name="HEAD Resultant",
            ),
        },
        "injury": {
            "hic15": _range(metrics.get("hic15_value"), metrics.get("hic15_start_time_s"), metrics.get("hic15_end_time_s")),
            "hic36": _range(metrics.get("hic36_value"), metrics.get("hic36_start_time_s"), metrics.get("hic36_end_time_s")),
            "one_peak_3ms": _range(metrics.get("one_peak_3ms_value"), metrics.get("one_peak_3ms_start_time_s"), metrics.get("one_peak_3ms_end_time_s"), unit=unit),
            "multiple_peak_3ms": _range(metrics.get("multiple_peak_3ms_value"), metrics.get("multiple_peak_3ms_start_time_s"), metrics.get("multiple_peak_3ms_end_time_s"), unit=unit),
            "resultant_peak": _point(metrics.get("resultant_peak_value"), metrics.get("resultant_peak_time_s"), unit=unit),
            "fmvss_head_80g_3ms_limit": {
                "duration_ms": _float_or_none(metrics.get("fmvss_head_acc_80g_3ms_duration_ms")),
                "status": _text(metrics.get("fmvss_head_acc_80g_3ms_status"), "-"),
                "limit_ms": 3.0,
            },
        },
    }


def _neck_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    display_names = dict(metrics.get("display_channel_names") or {})
    display_units = dict(metrics.get("display_units") or {})
    def _axis(axis_key):
        detail = dict((payload.get("metric_extrema") or {}).get(f"display_series.{axis_key}") or {})
        return _extrema(
            detail.get("max_value"),
            detail.get("max_time_s"),
            detail.get("min_value"),
            detail.get("min_time_s"),
            unit=display_units.get(axis_key) or ("N" if axis_key.startswith("F") else "Nm"),
            channel=(payload.get("channels") or {}).get(axis_key),
            display_name=display_names.get(axis_key) or axis_key,
        )
    criteria = dict(metrics.get("criteria") or {})
    return {
        "force": {
            "x": _axis("Fx"),
            "y": _axis("Fy"),
            "z": _axis("Fz"),
        },
        "moment": {
            "x": _axis("Mx"),
            "y": _axis("My"),
            "z": _axis("Mz"),
            "mocy": {
                "input": _text(criteria.get("input_moment"), "My"),
                "lever_arm_m": _float_or_none(criteria.get("moc_d")),
                "applied": bool(criteria.get("moc_applied")),
                "peak_flexion": _point(metrics.get("peak_flexion_my"), metrics.get("peak_flexion_time"), unit="Nm"),
                "peak_extension": _point(metrics.get("peak_extension_my"), metrics.get("peak_extension_time"), unit="Nm"),
            },
        },
        "injury": {
            "nte": _point(metrics.get("peak_nte"), metrics.get("peak_nte_time")),
            "ntf": _point(metrics.get("peak_ntf"), metrics.get("peak_ntf_time")),
            "nce": _point(metrics.get("peak_nce"), metrics.get("peak_nce_time")),
            "ncf": _point(metrics.get("peak_ncf"), metrics.get("peak_ncf_time")),
            "nij": {
                "overall": _point(metrics.get("overall_nij"), metrics.get("overall_nij_time")),
                "dominant_mode": _text(metrics.get("dominant_mode"), "-"),
            },
        },
    }


def _chest_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    channels = dict(payload.get("channels") or {})
    unit = "g"
    resultant_peak = dict(metrics.get("resultant_peak") or {})
    displacement_peak = dict(metrics.get("displacement_peak") or {})
    vc_sae_max = dict(metrics.get("vc_sae_max") or {})
    vc_sae_min = dict(metrics.get("vc_sae_min") or {})
    vc_ece_max = dict(metrics.get("vc_ece_max") or {})
    vc_ece_min = dict(metrics.get("vc_ece_min") or {})
    metric_extrema = dict(payload.get("metric_extrema") or {})
    resultant_extrema = dict(metric_extrema.get("resultant_g") or {})
    displacement_extrema = dict(metric_extrema.get("displacement_mm") or {})
    def _metric_extrema_block(key_name, *, channel="", display_name="", unit=""):
        detail = dict(metric_extrema.get(key_name) or {})
        return _extrema(
            detail.get("max_value"),
            detail.get("max_time_s"),
            detail.get("min_value"),
            detail.get("min_time_s"),
            unit=unit,
            channel=channel,
            display_name=display_name,
        )
    return {
        "acc": {
            "x": _metric_extrema_block("x_g", channel=channels.get("x"), display_name="ACC X", unit=unit),
            "y": _metric_extrema_block("y_g", channel=channels.get("y"), display_name="ACC Y", unit=unit),
            "z": _metric_extrema_block("z_g", channel=channels.get("z"), display_name="ACC Z", unit=unit),
            "resultant": _extrema(
                resultant_extrema.get("max_value"),
                resultant_extrema.get("max_time_s"),
                resultant_extrema.get("min_value"),
                resultant_extrema.get("min_time_s"),
                unit=unit,
                display_name="CHEST Resultant",
            ),
        },
        "displacement": {
            "channel": _text(channels.get("disp")),
            "unit": "mm",
            "max": _point(displacement_extrema.get("max_value"), displacement_extrema.get("max_time_s"), unit="mm"),
            "min": _point(displacement_extrema.get("min_value"), displacement_extrema.get("min_time_s"), unit="mm"),
            "peak": _point(displacement_peak.get("value"), displacement_peak.get("time_s"), unit="mm"),
        },
        "vc": {
            "sae_j1727_cfc600": {
                "max": _point(vc_sae_max.get("value"), vc_sae_max.get("time_s"), unit="m/s"),
                "min": _point(vc_sae_min.get("value"), vc_sae_min.get("time_s"), unit="m/s"),
            },
            "ece94_cfc180": {
                "max": _point(vc_ece_max.get("value"), vc_ece_max.get("time_s"), unit="m/s"),
                "min": _point(vc_ece_min.get("value"), vc_ece_min.get("time_s"), unit="m/s"),
            },
        },
        "injury": {
            "one_peak_3ms": _range(
                (metrics.get("one_peak_3ms_detail") or {}).get("value"),
                (metrics.get("one_peak_3ms_detail") or {}).get("start_time_s"),
                (metrics.get("one_peak_3ms_detail") or {}).get("end_time_s"),
                unit=unit,
            ),
            "multiple_peak_3ms": _range(
                (metrics.get("multiple_peak_3ms_detail") or {}).get("value"),
                (metrics.get("multiple_peak_3ms_detail") or {}).get("start_time_s"),
                (metrics.get("multiple_peak_3ms_detail") or {}).get("end_time_s"),
                unit=unit,
            ),
            "resultant_peak": _point(resultant_peak.get("value"), resultant_peak.get("time_s"), unit=unit),
        },
    }


def build_canonical_metrics(section_key, payload, metrics):
    section = _text(section_key).lower()
    if section == "head":
        return _head_canonical(payload, metrics)
    if section == "neck":
        return _neck_canonical(payload, metrics)
    if section == "chest":
        return _chest_canonical(payload, metrics)
    return {}
