# Naming contract:
# - definition key: "fmvss208"
# - display label: "FMVSS 208"
# - Excel template key: "fmvss208_summary"
FMVSS_208_NAME = "FMVSS 208"


def _item(
    result_key,
    label,
    module_key,
    section_key,
    value_key,
    *,
    unit="",
    payload_aliases=(),
    time_key=None,
    time_aliases=(),
    time_start_key=None,
    time_start_aliases=(),
    time_end_key=None,
    time_end_aliases=(),
    limit_key=None,
    limit_value=None,
    comparison="<=",
    value_transform=None,
):
    return {
        "result_key": result_key,
        "label": label,
        "module_key": module_key,
        "section_key": section_key,
        "value_key": value_key,
        "payload_aliases": tuple(payload_aliases or ()),
        "time_key": time_key,
        "time_aliases": tuple(time_aliases or ()),
        "time_start_key": time_start_key,
        "time_start_aliases": tuple(time_start_aliases or ()),
        "time_end_key": time_end_key,
        "time_end_aliases": tuple(time_end_aliases or ()),
        "unit": unit,
        "limit_key": limit_key,
        "limit_value": limit_value,
        "comparison": comparison,
        "value_transform": value_transform,
    }


def _series_peak_item(result_key, label, module_key, section_key, series_key, peak_kind, *, unit="", limit_key=None, limit_value=None):
    value_field = "max" if peak_kind == "max" else "min"
    return _item(
        result_key,
        label,
        module_key,
        section_key,
        "",
        unit=unit,
        payload_aliases=(f"metric_extrema.{series_key}.{value_field}_value",),
        time_aliases=(f"metric_extrema.{series_key}.{value_field}_time_s",),
        limit_key=limit_key,
        limit_value=limit_value,
    )


def _detail_at_item(result_key, label, module_key, section_key, detail_key, *, unit="", limit_key=None, limit_value=None):
    return _item(
        result_key,
        label,
        module_key,
        section_key,
        "",
        unit=unit,
        payload_aliases=(f"{detail_key}.value",),
        time_aliases=(f"{detail_key}.time_s",),
        limit_key=limit_key,
        limit_value=limit_value,
    )


def _detail_range_item(result_key, label, module_key, section_key, detail_key, *, unit="", limit_key=None, limit_value=None):
    return _item(
        result_key,
        label,
        module_key,
        section_key,
        "",
        unit=unit,
        payload_aliases=(f"{detail_key}.value",),
        time_start_aliases=(f"{detail_key}.start_time_s", f"{detail_key}.start_time"),
        time_end_aliases=(f"{detail_key}.end_time_s", f"{detail_key}.end_time"),
        limit_key=limit_key,
        limit_value=limit_value,
    )


def _head_axis_items():
    rows = []
    axis_specs = (
        ("x", "HEAD ACC X"),
        ("y", "HEAD ACC Y"),
        ("z", "HEAD ACC Z"),
        ("resultant", "HEAD Resultant"),
    )
    for axis_key, label_prefix in axis_specs:
        rows.append(
            _item(
                f"head.{axis_key}_max",
                f"{label_prefix} Max",
                "head",
                "head",
                f"head_{axis_key}_max",
                unit="g",
                payload_aliases=(f"head_{axis_key}_max_value",),
                time_aliases=(f"head_{axis_key}_max_time_s",),
            )
        )
        rows.append(
            _item(
                f"head.{axis_key}_min",
                f"{label_prefix} Min",
                "head",
                "head",
                f"head_{axis_key}_min",
                unit="g",
                payload_aliases=(f"head_{axis_key}_min_value",),
                time_aliases=(f"head_{axis_key}_min_time_s",),
            )
        )
    return tuple(rows)


def _neck_axis_items():
    rows = []
    axis_specs = (
        ("display_series.Fx", "NECK Fx MAX(Rear Shear)", "NECK Fx MIN(Forward Shear)"),
        ("display_series.Fy", "NECK Fy Max", "NECK Fy Min"),
        ("display_series.Fz", "NECK Fz MAX(Tension)", "NECK Fz MIN(Compression)"),
        ("display_series.Mx", "NECK Mx Max", "NECK Mx Min"),
        ("display_series.My", "NECK My MAX(Flexion)", "NECK My MIN(Extension)"),
        ("display_series.Mz", "NECK Mz Max", "NECK Mz Min"),
    )
    for series_key, max_label, min_label in axis_specs:
        suffix = series_key.split(".")[-1].lower()
        unit = "N" if suffix.startswith("f") else "Nm"
        rows.append(_series_peak_item(f"neck.{suffix}_max", max_label, "neck", "neck", series_key, "max", unit=unit))
        rows.append(_series_peak_item(f"neck.{suffix}_min", min_label, "neck", "neck", series_key, "min", unit=unit))
    return tuple(rows)


def _chest_axis_items():
    rows = []
    for axis_key, label_prefix in (("x_g", "CHEST ACC X"), ("y_g", "CHEST ACC Y"), ("z_g", "CHEST ACC Z")):
        rows.append(_series_peak_item(f"chest.{axis_key}_max", f"{label_prefix} Max", "chest", "chest", axis_key, "max", unit="g"))
        rows.append(_series_peak_item(f"chest.{axis_key}_min", f"{label_prefix} Min", "chest", "chest", axis_key, "min", unit="g"))
    rows.append(_series_peak_item("chest.displacement_max", "Chest Displacement Max", "chest", "chest", "displacement_mm", "max", unit="mm"))
    rows.append(_series_peak_item("chest.displacement_min", "Chest Displacement Min", "chest", "chest", "displacement_mm", "min", unit="mm"))
    return tuple(rows)


def _pelvis_axis_items():
    rows = []
    for axis_key, label_prefix in (("x_plot", "PELVIS ACC X"), ("y_plot", "PELVIS ACC Y"), ("z_plot", "PELVIS ACC Z")):
        rows.append(_series_peak_item(f"pelvis.{axis_key}_max", f"{label_prefix} Max", "pelvis", "pelvis", axis_key, "max", unit="g"))
        rows.append(_series_peak_item(f"pelvis.{axis_key}_min", f"{label_prefix} Min", "pelvis", "pelvis", axis_key, "min", unit="g"))
    return tuple(rows)


def _femur_axis_items():
    return (
        _series_peak_item("femur.left_force_max", "FEMUR LEFT Max", "femur", "femur", "left_force_n", "max", unit="N"),
        _series_peak_item("femur.left_force_min", "FEMUR LEFT Min", "femur", "femur", "left_force_n", "min", unit="N"),
        _series_peak_item("femur.right_force_max", "FEMUR RIGHT Max", "femur", "femur", "right_force_n", "max", unit="N"),
        _series_peak_item("femur.right_force_min", "FEMUR RIGHT Min", "femur", "femur", "right_force_n", "min", unit="N"),
    )


FMVSS_208_ITEMS = (
    *_head_axis_items(),
    _item(
        "head.hic15",
        "HIC15ms",
        "head",
        "head",
        "hic15",
        payload_aliases=("hic15_value",),
        time_start_aliases=("hic15_start_time_s", "hic15_start_time"),
        time_end_aliases=("hic15_end_time_s", "hic15_end_time"),
        limit_key="hic15_limit",
    ),
    _item(
        "head.hic36",
        "HIC36ms",
        "head",
        "head",
        "hic36",
        payload_aliases=("hic36_value",),
        time_start_aliases=("hic36_start_time_s", "hic36_start_time"),
        time_end_aliases=("hic36_end_time_s", "hic36_end_time"),
        limit_key="hic36_limit",
    ),
    _item(
        "head.one_peak_3ms",
        "One Peak 3ms",
        "head",
        "head",
        "head_one_peak_3ms",
        unit="g",
        payload_aliases=("one_peak_3ms_value", "clip3_value"),
        time_start_aliases=("one_peak_3ms_start_time_s",),
        time_end_aliases=("one_peak_3ms_end_time_s",),
        limit_key="head_3ms_limit_g",
    ),
    _item(
        "head.multiple_peak_3ms",
        "Multiple Peak 3ms",
        "head",
        "head",
        "head_multiple_3ms_clip",
        unit="g",
        payload_aliases=("multiple_peak_3ms_value",),
        time_start_aliases=("multiple_peak_3ms_start_time_s",),
        time_end_aliases=("multiple_peak_3ms_end_time_s",),
        limit_key="head_3ms_limit_g",
    ),
    _item(
        "head.resultant_acc_peak",
        "Resultant Acc. Peak",
        "head",
        "head",
        "resultant_peak_g",
        unit="g",
        payload_aliases=("resultant_peak_value", "resultant_peak.value"),
        time_aliases=("resultant_peak_time_s", "resultant_peak.time_s"),
        limit_key="head_3ms_limit_g",
    ),
    _item(
        "head.acceleration_80g_3ms_limit",
        "Head Acceleration 80g / 3ms Limit",
        "head",
        "head",
        "head_accel_80g_3ms_duration_ms",
        unit="ms",
        payload_aliases=("fmvss_head_acc_80g_3ms_duration_ms",),
        limit_value=3.0,
    ),

    *_neck_axis_items(),
    _item(
        "neck.peak_tension",
        "Peak Tension Force(FZ+)",
        "neck",
        "neck",
        "peak_tension_fz",
        unit="N",
        time_aliases=("peak_tension_time",),
        limit_key="peak_tension_limit",
    ),
    _item(
        "neck.peak_compression",
        "Peak Compression Force(FZ-)",
        "neck",
        "neck",
        "peak_compression_fz",
        unit="N",
        time_aliases=("peak_compression_time",),
        limit_key="peak_compression_limit",
    ),
    _item(
        "neck.peak_extension_mocy",
        "Peak Extension MOCy",
        "neck",
        "neck",
        "peak_extension_my",
        unit="Nm",
        time_aliases=("peak_extension_time",),
        limit_key="MyE",
    ),
    _item(
        "neck.peak_flexion_mocy",
        "Peak Flexion MOCy",
        "neck",
        "neck",
        "peak_flexion_my",
        unit="Nm",
        time_aliases=("peak_flexion_time",),
        limit_key="MyF",
    ),
    _item("neck.nte", "NTE", "neck", "neck", "peak_nte", time_aliases=("peak_nte_time",), limit_value=1.0),
    _item("neck.ntf", "NTF", "neck", "neck", "peak_ntf", time_aliases=("peak_ntf_time",), limit_value=1.0),
    _item("neck.nce", "NCE", "neck", "neck", "peak_nce", time_aliases=("peak_nce_time",), limit_value=1.0),
    _item("neck.ncf", "NCF", "neck", "neck", "peak_ncf", time_aliases=("peak_ncf_time",), limit_value=1.0),
    _item("neck.nij", "Overall Nij", "neck", "neck", "overall_nij", time_aliases=("overall_nij_time",), limit_value=1.0),

    *_chest_axis_items(),
    _item(
        "chest.one_peak_3ms",
        "One Peak 3ms",
        "chest",
        "chest",
        "chest_one_peak_3ms",
        unit="g",
        payload_aliases=("one_peak_3ms_g", "one_peak_3ms_detail.value"),
        time_start_aliases=("one_peak_3ms_detail.start_time_s",),
        time_end_aliases=("one_peak_3ms_detail.end_time_s",),
        limit_key="accel_3ms_limit_g",
    ),
    _item(
        "chest.multiple_peak_3ms",
        "Multiple Peak 3ms",
        "chest",
        "chest",
        "chest_multiple_3ms_clip",
        unit="g",
        payload_aliases=("multiple_peak_3ms_g", "multiple_peak_3ms_detail.value"),
        time_start_aliases=("multiple_peak_3ms_detail.start_time_s",),
        time_end_aliases=("multiple_peak_3ms_detail.end_time_s",),
        limit_key="accel_3ms_limit_g",
    ),
    _item(
        "chest.acc_peak",
        "Resultant Acc. Peak",
        "chest",
        "chest",
        "resultant_peak_g",
        unit="g",
        payload_aliases=("resultant_peak.value",),
        time_aliases=("resultant_peak.time_s",),
        limit_key="accel_3ms_limit_g",
    ),
    _item(
        "chest.deflection_peak",
        "Chest Deflection Peak",
        "chest",
        "chest",
        "displacement_peak_mm",
        unit="mm",
        payload_aliases=("displacement_peak.value",),
        time_aliases=("displacement_peak.time_s",),
        limit_key="deflection_limit_mm",
    ),
    _item(
        "chest.vc_sae_max",
        "V*C SAE J1727_CFC600 Max",
        "chest",
        "chest",
        "vc_sae_max_mps",
        unit="m/s",
        payload_aliases=("vc_sae_max.value",),
        time_aliases=("vc_sae_max.time_s",),
        limit_key="vc_limit_mps",
    ),
    _detail_at_item("chest.vc_sae_min", "V*C SAE J1727_CFC600 Min", "chest", "chest", "vc_sae_min", unit="m/s"),
    _item(
        "chest.vc_ece_max",
        "V*C ECE94_CFC180 Max",
        "chest",
        "chest",
        "vc_ece_max_mps",
        unit="m/s",
        payload_aliases=("vc_ece_max.value",),
        time_aliases=("vc_ece_max.time_s",),
        limit_key="vc_limit_mps",
    ),
    _detail_at_item("chest.vc_ece_min", "V*C ECE94_CFC180 Min", "chest", "chest", "vc_ece_min", unit="m/s"),

    *_pelvis_axis_items(),
    _detail_range_item("pelvis.one_peak_3ms_clip", "One Peak 3ms_Clip", "pelvis", "pelvis", "one_peak_3ms", unit="g"),
    _detail_range_item("pelvis.multiple_peak_3ms_clip", "Multiple Peak 3ms_Clip", "pelvis", "pelvis", "multiple_peak_3ms", unit="g"),
    _item(
        "pelvis.resultant_peak",
        "Resultant Acc. Peak",
        "pelvis",
        "pelvis",
        "pelvis_resultant_peak",
        unit="g",
        payload_aliases=("resultant_peak.value",),
        time_aliases=("resultant_peak.time_s",),
    ),

    *_femur_axis_items(),
    _item(
        "femur.left_peak",
        "Left Peak Axial Force",
        "femur",
        "femur",
        "left_peak_axial_force_n",
        unit="N",
        payload_aliases=("left_peak_abs.value",),
        time_aliases=("left_peak_abs.time_s",),
        limit_key="femur_force_limit_n",
    ),
    _item(
        "femur.right_peak",
        "Right Peak Axial Force",
        "femur",
        "femur",
        "right_peak_axial_force_n",
        unit="N",
        payload_aliases=("right_peak_abs.value",),
        time_aliases=("right_peak_abs.time_s",),
        limit_key="femur_force_limit_n",
    ),

    _item(
        "knee.left_displacement_peak",
        "Left KNEE Displacement Peak",
        "knee",
        "knee",
        "left_peak_slider",
        unit="mm",
        time_aliases=("left_peak_slider_time_s", "left_peak.time_s"),
        limit_key="slider_displacement_limit_mm",
    ),
    _item(
        "knee.right_displacement_peak",
        "Right KNEE Displacement Peak",
        "knee",
        "knee",
        "right_peak_slider",
        unit="mm",
        time_aliases=("right_peak_slider_time_s", "right_peak.time_s"),
        limit_key="slider_displacement_limit_mm",
    ),
)


FMVSS_208_DEFINITION = {
    "key": "fmvss208",
    "label": FMVSS_208_NAME,
    "items": FMVSS_208_ITEMS,
    "source_notes": (
        "CrashAnalysisCriteria 2.4.3 head criteria pages 10-12",
        "CrashAnalysisCriteria 2.4.3 neck criteria pages 35-40",
        "CrashAnalysisCriteria 2.4.3 chest criteria pages 63-66",
        "app/core/dummy/engine.py FMVSS 208 module factors",
    ),
}
