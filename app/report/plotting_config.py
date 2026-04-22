from pathlib import Path


PLOTTING_TEMPLATE_FILENAME = "testid_Plot.pptx"


def resolve_plotting_template_path():
    module_path = Path(__file__).resolve()
    repo_root = module_path.parents[2]
    candidate = repo_root / "resources" / "templates" / PLOTTING_TEMPLATE_FILENAME
    return candidate


PLOTTING_TEMPLATE_PATH = resolve_plotting_template_path()


PLOTTING_OUTPUT_SUFFIX = "_Plot"
PLOTTING_SAVE_SUFFIX = "_P"
PLOTTING_CACHE_KEY = "plotting_report"


COMMON_REPORT_FIELD_ORDER = (
    ("manufacturer", "Manufacturer"),
    ("vehicle", "Vehicle"),
    ("speed", "Speed"),
    ("test_date", "Test Date"),
    ("test_id", "Test ID"),
)

PLOTTING_TEMPLATE_TEXT_MARKERS = {
    "test_id_title": "TEST ID",
    "graph_header": "Graph header name",
    "report_fields": "Test ID :",
    "injury_text": "Input txt",
    "plot_box": "Plot here",
}


PLOTTING_GRAPH_TEXT_RULES = {
    ("head", "head_xyz"): {
        "template": "acc_axes_then_resultant",
        "axis_keys": ("x", "y", "z"),
        "resultant_key": "head_resultant",
        "resultant_label": "HEAD Resultant",
        "resultant_max_value_key": "head_resultant_max",
        "resultant_max_time_key": "head_resultant_max_time_s",
        "resultant_min_value_key": "head_resultant_min",
        "resultant_min_time_key": "head_resultant_min_time_s",
        "unit": "g",
    },
    ("head", "head_resultant"): {
        "template": "head_resultant_injuries",
        "injury_lines": (
            {"type": "range", "label": "HIC15", "value_key": "hic15_value", "start_key": "hic15_start_time_s", "end_key": "hic15_end_time_s", "unit": ""},
            {"type": "range", "label": "HIC36", "value_key": "hic36_value", "start_key": "hic36_start_time_s", "end_key": "hic36_end_time_s", "unit": ""},
            {"type": "range", "label": "One Peak 3ms_Clip", "value_key": "one_peak_3ms_value", "start_key": "one_peak_3ms_start_time_s", "end_key": "one_peak_3ms_end_time_s", "unit": "g"},
            {"type": "range", "label": "Multiple Peak 3ms_Clip", "value_key": "multiple_peak_3ms_value", "start_key": "multiple_peak_3ms_start_time_s", "end_key": "multiple_peak_3ms_end_time_s", "unit": "g"},
            {"type": "at", "label": "Resultant Acc. Peak", "value_key": "resultant_peak_value", "time_key": "resultant_peak_time_s", "unit": "g"},
            {"type": "fmvss_head_80g"},
        ),
    },
    ("chest", "accel"): {
        "template": "acc_axes_then_injuries",
        "axis_keys": ("x", "y", "z"),
        "resultant_key": "resultant_g",
        "resultant_label": "CHEST Resultant",
        "unit": "g",
        "injury_lines": (
            {"type": "range", "label": "One Peak 3ms_Clip", "detail_key": "one_peak_3ms_detail", "unit": "g"},
            {"type": "range", "label": "Multiple Peak 3ms_Clip", "detail_key": "multiple_peak_3ms_detail", "unit": "g"},
            {"type": "detail_at", "label": "Resultant Acc. Peak", "detail_key": "resultant_peak", "unit": "g"},
        ),
    },
    ("chest", "disp"): {
        "template": "chest_displacement_summary",
    },
    ("chest", "vc"): {
        "template": "chest_vc_summary",
    },
    ("pelvis", "accel_resultant"): {
        "template": "acc_axes_then_injuries",
        "axis_keys": ("x", "y", "z"),
        "resultant_key": "resultant",
        "resultant_label": "PELVIS Resultant",
        "unit": "g",
        "injury_lines": (
            {"type": "detail_range", "label": "One Peak 3ms_Clip", "detail_key": "one_peak_3ms", "unit": "g"},
            {"type": "detail_range", "label": "Multiple Peak 3ms_Clip", "detail_key": "multiple_peak_3ms", "unit": "g"},
            {"type": "detail_at", "label": "Resultant Acc. Peak", "detail_key": "resultant_peak", "unit": "g"},
        ),
    },
    ("neck", "fo"): {
        "template": "neck_force_axes",
        "axis_keys": ("Fx", "Fy", "Fz"),
        "title": "UPPER NECK FORCE",
    },
    ("neck", "mo"): {
        "template": "neck_moment_axes",
        "axis_keys": ("Mx", "My", "Mz"),
        "title": "UPPER NECK MOMENT",
    },
    ("neck", "mocy"): {
        "template": "neck_mocy_summary",
    },
    ("neck", "nij_components"): {
        "template": "neck_nij_components_summary",
    },
    ("neck", "nij_overall"): {
        "template": "neck_nij_overall_summary",
    },
}
