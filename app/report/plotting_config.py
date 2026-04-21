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
        "template": "acc_axes",
        "axis_keys": ("x", "y", "z"),
    },
    ("head", "head_resultant"): {
        "template": "acc_resultant_with_injuries",
        "resultant_key": "head_resultant",
        "resultant_label": "HEAD Resultant",
        "unit": "g",
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
}
