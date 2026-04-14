FMVSS_208_NAME = "FMVSS 208"


FMVSS_208_ITEMS = (
    {
        "result_key": "head.hic15",
        "label": "Head HIC15",
        "module_key": "head",
        "section_key": "head",
        "value_key": "hic15",
        "payload_aliases": ("hic15_value",),
        "unit": "-",
        "limit_key": "hic15_limit",
        "comparison": "<=",
    },
    {
        "result_key": "head.hic36",
        "label": "Head HIC36",
        "module_key": "head",
        "section_key": "head",
        "value_key": "hic36",
        "payload_aliases": ("hic36_value",),
        "unit": "-",
        "limit_key": "hic36_limit",
        "comparison": "<=",
    },
    {
        "result_key": "head.3ms_clip",
        "label": "Head 3ms Clip",
        "module_key": "head",
        "section_key": "head",
        "value_key": "head_3ms_clip",
        "payload_aliases": ("one_peak_3ms_value", "clip3_value"),
        "unit": "g",
        "limit_key": "head_3ms_limit_g",
        "comparison": "<=",
    },
    {
        "result_key": "neck.nij",
        "label": "Neck Nij",
        "module_key": "neck",
        "section_key": "neck",
        "value_key": "overall_nij",
        "unit": "-",
        "limit_value": 1.0,
        "comparison": "<=",
        "summary_label": "Overall Nij",
    },
    {
        "result_key": "neck.peak_tension",
        "label": "Neck Peak Tension",
        "module_key": "neck",
        "section_key": "neck",
        "value_key": "peak_tension_fz",
        "unit": "N",
        "limit_key": "peak_tension_limit",
        "comparison": "<=",
        "summary_label": "Peak Tension Force (FZ+)",
    },
    {
        "result_key": "neck.peak_compression",
        "label": "Neck Peak Compression",
        "module_key": "neck",
        "section_key": "neck",
        "value_key": "peak_compression_fz",
        "unit": "N",
        "limit_key": "peak_compression_limit",
        "comparison": "<=",
        "summary_label": "Peak Comp. Force (FZ-)",
    },
    {
        "result_key": "chest.3ms_clip",
        "label": "Chest 3ms Clip",
        "module_key": "chest",
        "section_key": "chest",
        "value_key": "chest_3ms_clip",
        "payload_aliases": ("one_peak_3ms_g", "one_peak_3ms_detail.value"),
        "unit": "g",
        "limit_key": "accel_3ms_limit_g",
        "comparison": "<=",
        "summary_label": "One Peak 3ms_Clip",
    },
    {
        "result_key": "chest.deflection_peak",
        "label": "Chest Deflection Peak",
        "module_key": "chest",
        "section_key": "chest",
        "value_key": "displacement_peak_mm",
        "payload_aliases": ("displacement_peak.value",),
        "unit": "mm",
        "limit_key": "deflection_limit_mm",
        "comparison": "<=",
        "summary_label": "Displacement Peak",
    },
    {
        "result_key": "femur.left_peak",
        "label": "Femur Left Peak Axial Force",
        "module_key": "femur",
        "section_key": "femur",
        "value_key": "left_peak_axial_force_n",
        "payload_aliases": ("left_peak_abs.value",),
        "unit": "N",
        "limit_key": "femur_force_limit_n",
        "comparison": "<=",
        "summary_label": "Left Peak Axial Force",
    },
    {
        "result_key": "femur.right_peak",
        "label": "Femur Right Peak Axial Force",
        "module_key": "femur",
        "section_key": "femur",
        "value_key": "right_peak_axial_force_n",
        "payload_aliases": ("right_peak_abs.value",),
        "unit": "N",
        "limit_key": "femur_force_limit_n",
        "comparison": "<=",
        "summary_label": "Right Peak Axial Force",
    },
)


REGULATION_DEFINITIONS = {
    FMVSS_208_NAME: {
        "key": "fmvss208",
        "label": FMVSS_208_NAME,
        "items": FMVSS_208_ITEMS,
        "source_notes": (
            "CrashAnalysisCriteria 2.4.3 neck NIC pages 34-36",
            "SafetyCompanion 2024 U.S. frontal criteria summary page 50",
            "app/core/dummy/engine.py FMVSS 208 module factors",
        ),
    },
}


def get_regulation_choices():
    return tuple(REGULATION_DEFINITIONS.keys())


def get_regulation_definition(name):
    return REGULATION_DEFINITIONS.get(str(name or "").strip())
