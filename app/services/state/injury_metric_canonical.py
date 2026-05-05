"""Canonical injury metric payload helpers.

This module normalizes section-specific computed results into a shared
`section + metric + axis/component` structure so formatters can stop depending
on legacy per-module field names over time. It also stores calculation context
separately from computed metric payloads so formatters can explain how a result
was produced without re-reading UI state.
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


def _extrema(max_value=None, max_time_s=None, min_value=None, min_time_s=None, unit="", channel="", display_name="", abs_peak_value=None, abs_peak_time_s=None):
    result = {
        "channel": _text(channel),
        "display_name": _text(display_name),
        "unit": _text(unit),
        "max": _point(max_value, max_time_s, unit=unit),
        "min": _point(min_value, min_time_s, unit=unit),
    }
    if abs_peak_value is not None or abs_peak_time_s is not None:
        result["abs_peak"] = _point(abs_peak_value, abs_peak_time_s, unit=unit)
    return result


def _channel_input_entry(channel_name="", *, axis=None, role=None, unit=None):
    entry = {
        "channel": _text(channel_name),
        "axis": _text(axis),
        "role": _text(role),
    }
    if unit is not None:
        entry["unit"] = _text(unit)
    return entry


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


def _pelvis_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    channels = dict(payload.get("channels") or {})
    unit = _text(metrics.get("plot_unit") or payload.get("report_values", {}).get("plot_unit") or "g", "g")
    metric_extrema = dict(payload.get("metric_extrema") or {})

    def _axis(key_name, channel_key, display_name):
        detail = dict(metric_extrema.get(key_name) or {})
        return _extrema(
            detail.get("max_value"),
            detail.get("max_time_s"),
            detail.get("min_value"),
            detail.get("min_time_s"),
            unit=unit,
            channel=channels.get(channel_key),
            display_name=display_name,
        )

    return {
        "acc": {
            "x": _axis("x_plot", "x", "ACC X"),
            "y": _axis("y_plot", "y", "ACC Y"),
            "z": _axis("z_plot", "z", "ACC Z"),
            "resultant": _extrema(
                dict(metric_extrema.get("resultant") or {}).get("max_value"),
                dict(metric_extrema.get("resultant") or {}).get("max_time_s"),
                dict(metric_extrema.get("resultant") or {}).get("min_value"),
                dict(metric_extrema.get("resultant") or {}).get("min_time_s"),
                unit=unit,
                display_name="PELVIS Resultant",
            ),
        },
        "injury": {
            "one_peak_3ms": _range(
                (metrics.get("one_peak_3ms") or {}).get("value"),
                (metrics.get("one_peak_3ms") or {}).get("start_time_s"),
                (metrics.get("one_peak_3ms") or {}).get("end_time_s"),
                unit=unit,
            ),
            "multiple_peak_3ms": _range(
                (metrics.get("multiple_peak_3ms") or {}).get("value"),
                (metrics.get("multiple_peak_3ms") or {}).get("start_time_s"),
                (metrics.get("multiple_peak_3ms") or {}).get("end_time_s"),
                unit=unit,
            ),
            "resultant_peak": _point(
                (metrics.get("resultant_peak") or {}).get("value"),
                (metrics.get("resultant_peak") or {}).get("time_s"),
                unit=unit,
            ),
        },
    }


def _femur_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    channels = dict(payload.get("channels") or {})
    metric_extrema = dict(payload.get("metric_extrema") or {})
    criteria = dict(metrics.get("criteria") or {})

    def _force_side(side_key):
        series_key = f"{side_key}_force_n"
        detail = dict(metric_extrema.get(series_key) or {})
        return _extrema(
            detail.get("max_value"),
            detail.get("max_time_s"),
            detail.get("min_value"),
            detail.get("min_time_s"),
            unit="N",
            channel=channels.get(side_key),
            display_name=f"FEMUR {side_key.upper()}",
        )

    return {
        "force": {
            "left": _force_side("left"),
            "right": _force_side("right"),
        },
        "injury": {
            "left_peak": _point((metrics.get("left_peak_abs") or {}).get("value"), (metrics.get("left_peak_abs") or {}).get("time_s"), unit="N"),
            "right_peak": _point((metrics.get("right_peak_abs") or {}).get("value"), (metrics.get("right_peak_abs") or {}).get("time_s"), unit="N"),
            "overall_peak": _point((metrics.get("overall_peak") or {}).get("value"), (metrics.get("overall_peak") or {}).get("time_s"), unit="N"),
        },
        "criteria": {
            "femur_force_limit_n": _float_or_none(criteria.get("femur_force_limit_n")),
            "required_cfc": _float_or_none(criteria.get("required_cfc")),
            "passes_limit": bool(metrics.get("passes_limit")),
        },
    }


def _knee_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    channels = dict(payload.get("channels") or {})
    unit = _text(metrics.get("plot_unit") or "mm", "mm")
    return {
        "displacement": {
            "left": {
                "channel": _text(channels.get("left")),
                "peak": _point((metrics.get("left_peak") or {}).get("value"), (metrics.get("left_peak") or {}).get("time_s"), unit=unit),
            },
            "right": {
                "channel": _text(channels.get("right")),
                "peak": _point((metrics.get("right_peak") or {}).get("value"), (metrics.get("right_peak") or {}).get("time_s"), unit=unit),
            },
        }
    }


def _iliac_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    channels = dict(payload.get("channels") or {})
    left = dict(metrics.get("left_summary") or {})
    right = dict(metrics.get("right_summary") or {})
    return {
        "force": {
            "left_fx": _extrema(
                left.get("tension_force_n"),
                left.get("tension_time_s"),
                left.get("compression_force_n"),
                left.get("compression_time_s"),
                unit="N",
                channel=_text(channels.get("left_fx")),
                display_name="Fx",
                abs_peak_value=left.get("peak_force_n"),
                abs_peak_time_s=left.get("peak_force_time_s"),
            ),
            "right_fx": _extrema(
                right.get("tension_force_n"),
                right.get("tension_time_s"),
                right.get("compression_force_n"),
                right.get("compression_time_s"),
                unit="N",
                channel=_text(channels.get("right_fx")),
                display_name="Fx",
                abs_peak_value=right.get("peak_force_n"),
                abs_peak_time_s=right.get("peak_force_time_s"),
            ),
        },
        "moment": {
            "left_my": _extrema(
                left.get("max_moment_nm"),
                left.get("max_moment_time_s"),
                left.get("min_moment_nm"),
                left.get("min_moment_time_s"),
                unit="Nm",
                channel=_text(channels.get("left_my")),
                display_name="My",
                abs_peak_value=left.get("peak_moment_nm"),
                abs_peak_time_s=left.get("peak_moment_time_s"),
            ),
            "right_my": _extrema(
                right.get("max_moment_nm"),
                right.get("max_moment_time_s"),
                right.get("min_moment_nm"),
                right.get("min_moment_time_s"),
                unit="Nm",
                channel=_text(channels.get("right_my")),
                display_name="My",
                abs_peak_value=right.get("peak_moment_nm"),
                abs_peak_time_s=right.get("peak_moment_time_s"),
            ),
        },
    }


def _tibia_station_context(metrics, station_key):
    station = dict(metrics.get(station_key) or {})
    return {
        "peak_tibia_index": _point((station.get("peak_tibia_index") or {}).get("value"), (station.get("peak_tibia_index") or {}).get("time_s")),
        "peak_compression": _point((station.get("peak_compression") or {}).get("value"), (station.get("peak_compression") or {}).get("time_s"), unit="N"),
        "peak_moment_resultant": _point((station.get("peak_moment_resultant") or {}).get("value"), (station.get("peak_moment_resultant") or {}).get("time_s"), unit="Nm"),
    }


def _tibia_canonical(payload, metrics):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    return {
        "injury": {
            "left_upper": _tibia_station_context(metrics, "left_upper"),
            "left_lower": _tibia_station_context(metrics, "left_lower"),
            "right_upper": _tibia_station_context(metrics, "right_upper"),
            "right_lower": _tibia_station_context(metrics, "right_lower"),
            "overall_peak": _point((metrics.get("overall_peak_tibia_index") or {}).get("value"), (metrics.get("overall_peak_tibia_index") or {}).get("time_s")),
        },
        "criteria": {
            "force_crit_n": _float_or_none(metrics.get("force_crit_n")),
            "moment_crit_nm": _float_or_none(metrics.get("moment_crit_nm")),
            "ti_reference_line": _float_or_none(metrics.get("ti_reference_line")),
            "ti_secondary_line": _float_or_none(metrics.get("ti_secondary_line")),
            "overall_peak_label": _text(metrics.get("overall_peak_label")),
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
    if section == "pelvis":
        return _pelvis_canonical(payload, metrics)
    if section == "femur":
        return _femur_canonical(payload, metrics)
    if section == "knee":
        return _knee_canonical(payload, metrics)
    if section == "iliac":
        return _iliac_canonical(payload, metrics)
    if section == "tibia":
        return _tibia_canonical(payload, metrics)
    return {}


def _head_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    return {
        "engine_key": "head_injury_bundle_v1",
        "rule_key": "head_hic",
        "section": "head",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": {
                "x": _channel_input_entry(channels.get("x"), axis="x", role="acc"),
                "y": _channel_input_entry(channels.get("y"), axis="y", role="acc"),
                "z": _channel_input_entry(channels.get("z"), axis="z", role="acc"),
            },
            "derived_channels": {
                "resultant": _channel_input_entry(payload.get("resultant_channel"), role="resultant"),
            },
        },
        "parameters": {
            "hic_windows_ms": (15, 36),
            "plot_unit": _text(payload.get("plot_unit") or payload.get("report_values", {}).get("plot_unit") or "g", "g"),
        },
        "flags": {
            "neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {}),
        },
    }


def _neck_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    criteria = dict(metrics.get("criteria") or {})
    return {
        "engine_key": "neck_injury_bundle_v1",
        "rule_key": "neck_nij",
        "section": "neck",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": {
                "Fx": _channel_input_entry(channels.get("Fx"), axis="x", role="force"),
                "Fy": _channel_input_entry(channels.get("Fy"), axis="y", role="force"),
                "Fz": _channel_input_entry(channels.get("Fz"), axis="z", role="force"),
                "Mx": _channel_input_entry(channels.get("Mx"), axis="x", role="moment"),
                "My": _channel_input_entry(channels.get("My"), axis="y", role="moment"),
                "Mz": _channel_input_entry(channels.get("Mz"), axis="z", role="moment"),
            },
        },
        "parameters": {
            "input_moment": _text(criteria.get("input_moment"), "My"),
            "moc_d_m": _float_or_none(criteria.get("moc_d")),
            "moc_applied": bool(criteria.get("moc_applied")),
        },
        "flags": {
            "neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {}),
        },
    }


def _chest_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    return {
        "engine_key": "chest_injury_bundle_v1",
        "rule_key": "chest_accel_disp_vc",
        "section": "chest",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": {
                "x": _channel_input_entry(channels.get("x"), axis="x", role="acc"),
                "y": _channel_input_entry(channels.get("y"), axis="y", role="acc"),
                "z": _channel_input_entry(channels.get("z"), axis="z", role="acc"),
                "disp": _channel_input_entry(channels.get("disp"), role="displacement"),
            },
        },
        "parameters": {
            "plot_unit": "g",
            "displacement_unit": "mm",
            "vc_variants": ("sae_j1727_cfc600", "ece94_cfc180"),
        },
        "flags": {
            "neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {}),
        },
    }


def _pelvis_context(payload, metrics, state):
    payload = dict(payload or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    return {
        "engine_key": "pelvis_injury_bundle_v1",
        "rule_key": "pelvis_accel_3ms",
        "section": "pelvis",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": {
                "x": _channel_input_entry(channels.get("x"), axis="x", role="acc"),
                "y": _channel_input_entry(channels.get("y"), axis="y", role="acc"),
                "z": _channel_input_entry(channels.get("z"), axis="z", role="acc"),
            },
        },
        "parameters": {
            "plot_unit": _text((metrics or {}).get("plot_unit") or "g", "g"),
        },
        "flags": {"neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {})},
    }


def _femur_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    criteria = dict(metrics.get("criteria") or {})
    return {
        "engine_key": "femur_injury_bundle_v1",
        "rule_key": "femur_axial_force",
        "section": "femur",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": {
                "left": _channel_input_entry(channels.get("left"), role="force"),
                "right": _channel_input_entry(channels.get("right"), role="force"),
            },
        },
        "parameters": {
            "femur_force_limit_n": _float_or_none(criteria.get("femur_force_limit_n")),
            "required_cfc": _float_or_none(criteria.get("required_cfc")),
        },
        "flags": {"neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {})},
    }


def _knee_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    return {
        "engine_key": "knee_injury_bundle_v1",
        "rule_key": "knee_slider_peak",
        "section": "knee",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": {
                "left": _channel_input_entry(channels.get("left"), role="slider"),
                "right": _channel_input_entry(channels.get("right"), role="slider"),
            },
        },
        "parameters": {
            "plot_unit": _text(metrics.get("plot_unit") or "mm", "mm"),
        },
        "flags": {"neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {})},
    }


def _iliac_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    return {
        "engine_key": "iliac_injury_bundle_v1",
        "rule_key": "iliac_force_moment",
        "section": "iliac",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key") or metrics.get("criterion_key")),
        "inputs": {
            "channels": {
                "left_fx": _channel_input_entry(channels.get("left_fx"), role="force"),
                "left_my": _channel_input_entry(channels.get("left_my"), role="moment"),
                "right_fx": _channel_input_entry(channels.get("right_fx"), role="force"),
                "right_my": _channel_input_entry(channels.get("right_my"), role="moment"),
            },
        },
        "parameters": {
            "criterion_label": _text(metrics.get("criterion_label")),
            "criterion_source": _text(metrics.get("criterion_source")),
        },
        "flags": {"neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {})},
    }


def _tibia_context(payload, metrics, state):
    payload = dict(payload or {})
    metrics = dict(metrics or {})
    state = dict(state or {})
    channels = dict(payload.get("channels") or state.get("channels") or {})
    return {
        "engine_key": "tibia_injury_bundle_v1",
        "rule_key": "tibia_index",
        "section": "tibia",
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key") or metrics.get("criterion_key")),
        "inputs": {
            "channels": {key: _channel_input_entry(value) for key, value in channels.items()}
        },
        "parameters": {
            "criterion_label": _text(metrics.get("criterion_label")),
            "criterion_source": _text(metrics.get("criterion_source")),
            "force_crit_n": _float_or_none(metrics.get("force_crit_n")),
            "moment_crit_nm": _float_or_none(metrics.get("moment_crit_nm")),
        },
        "flags": {"neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {})},
    }


def build_canonical_context(section_key, payload, metrics, state=None):
    section = _text(section_key).lower()
    if section == "head":
        return _head_context(payload, metrics, state)
    if section == "neck":
        return _neck_context(payload, metrics, state)
    if section == "chest":
        return _chest_context(payload, metrics, state)
    if section == "pelvis":
        return _pelvis_context(payload, metrics, state)
    if section == "femur":
        return _femur_context(payload, metrics, state)
    if section == "knee":
        return _knee_context(payload, metrics, state)
    if section == "iliac":
        return _iliac_context(payload, metrics, state)
    if section == "tibia":
        return _tibia_context(payload, metrics, state)
    payload = dict(payload or {})
    state = dict(state or {})
    return {
        "engine_key": "",
        "rule_key": "",
        "section": section,
        "slot": _text(payload.get("slot") or state.get("slot")),
        "dummy_profile": _text(payload.get("dummy_profile") or state.get("dummy_profile")),
        "criterion_key": _text(payload.get("criterion_key") or state.get("criterion_key")),
        "inputs": {
            "channels": dict(payload.get("channels") or state.get("channels") or {}),
        },
        "parameters": {},
        "flags": {
            "neg_flags": dict(payload.get("neg_flags") or state.get("neg_flags") or {}),
        },
    }


def build_canonical_graphs(section_key):
    section = _text(section_key).lower()
    if section == "head":
        return {
            "head_xyz": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.acc.x",
                    "metrics.acc.y",
                    "metrics.acc.z",
                    "metrics.acc.resultant",
                ),
                "annotations": tuple(),
            },
            "head_resultant": {
                "graph_type": "single",
                "series_refs": ("metrics.acc.resultant",),
                "annotations": (
                    "metrics.injury.hic15",
                    "metrics.injury.hic36",
                    "metrics.injury.one_peak_3ms",
                    "metrics.injury.multiple_peak_3ms",
                    "metrics.injury.resultant_peak",
                    "metrics.injury.fmvss_head_80g_3ms_limit",
                ),
            },
        }
    if section == "neck":
        return {
            "fo": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.force.x",
                    "metrics.force.y",
                    "metrics.force.z",
                ),
                "annotations": (
                    "metrics.injury.nte",
                    "metrics.injury.ntf",
                    "metrics.injury.nce",
                    "metrics.injury.ncf",
                ),
            },
            "mo": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.moment.x",
                    "metrics.moment.y",
                    "metrics.moment.z",
                ),
                "annotations": tuple(),
            },
            "mocy": {
                "graph_type": "single",
                "series_refs": ("metrics.moment.mocy",),
                "annotations": (
                    "metrics.moment.mocy.peak_flexion",
                    "metrics.moment.mocy.peak_extension",
                ),
            },
            "nij_components": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.injury.nte",
                    "metrics.injury.ntf",
                    "metrics.injury.nce",
                    "metrics.injury.ncf",
                ),
                "annotations": ("metrics.injury.nij",),
            },
            "nij_overall": {
                "graph_type": "single",
                "series_refs": ("metrics.injury.nij",),
                "annotations": tuple(),
            },
        }
    if section == "chest":
        return {
            "accel": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.acc.x",
                    "metrics.acc.y",
                    "metrics.acc.z",
                    "metrics.acc.resultant",
                ),
                "annotations": (
                    "metrics.injury.one_peak_3ms",
                    "metrics.injury.multiple_peak_3ms",
                    "metrics.injury.resultant_peak",
                ),
            },
            "disp": {
                "graph_type": "single",
                "series_refs": ("metrics.displacement",),
                "annotations": ("metrics.displacement.peak",),
            },
            "vc": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.vc.sae_j1727_cfc600",
                    "metrics.vc.ece94_cfc180",
                ),
                "annotations": tuple(),
            },
        }
    if section == "pelvis":
        return {
            "accel_resultant": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.acc.x",
                    "metrics.acc.y",
                    "metrics.acc.z",
                    "metrics.acc.resultant",
                ),
                "annotations": (
                    "metrics.injury.one_peak_3ms",
                    "metrics.injury.multiple_peak_3ms",
                    "metrics.injury.resultant_peak",
                ),
            },
        }
    if section == "femur":
        return {
            "left": {"graph_type": "single", "series_refs": ("metrics.force.left",), "annotations": ("metrics.injury.left_peak",)},
            "right": {"graph_type": "single", "series_refs": ("metrics.force.right",), "annotations": ("metrics.injury.right_peak",)},
            "combined": {"graph_type": "overlay", "series_refs": ("metrics.force.left", "metrics.force.right"), "annotations": ("metrics.injury.left_peak", "metrics.injury.right_peak", "metrics.injury.overall_peak")},
        }
    if section == "knee":
        return {
            "combined": {"graph_type": "overlay", "series_refs": ("metrics.displacement.left", "metrics.displacement.right"), "annotations": tuple()},
        }
    if section == "iliac":
        return {
            "force": {"graph_type": "overlay", "series_refs": ("metrics.force.left_fx", "metrics.force.right_fx"), "annotations": tuple()},
            "moment": {"graph_type": "overlay", "series_refs": ("metrics.moment.left_my", "metrics.moment.right_my"), "annotations": tuple()},
        }
    if section == "tibia":
        return {
            "tibia_index": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.injury.left_upper.peak_tibia_index",
                    "metrics.injury.left_lower.peak_tibia_index",
                    "metrics.injury.right_upper.peak_tibia_index",
                    "metrics.injury.right_lower.peak_tibia_index",
                ),
                "annotations": ("metrics.injury.overall_peak",),
            },
            "axial_force": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.injury.left_upper.peak_compression",
                    "metrics.injury.left_lower.peak_compression",
                    "metrics.injury.right_upper.peak_compression",
                    "metrics.injury.right_lower.peak_compression",
                ),
                "annotations": tuple(),
            },
            "moment_resultant": {
                "graph_type": "overlay",
                "series_refs": (
                    "metrics.injury.left_upper.peak_moment_resultant",
                    "metrics.injury.left_lower.peak_moment_resultant",
                    "metrics.injury.right_upper.peak_moment_resultant",
                    "metrics.injury.right_lower.peak_moment_resultant",
                ),
                "annotations": tuple(),
            },
        }
    return {}
