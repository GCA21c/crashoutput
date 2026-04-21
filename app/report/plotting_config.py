from pathlib import Path


PLOTTING_TEMPLATE_FILENAME = "ReportPlotting_temp.pptx"


def resolve_plotting_template_path():
    module_path = Path(__file__).resolve()
    repo_root = module_path.parents[2]
    candidate = repo_root / "resources" / "templates" / PLOTTING_TEMPLATE_FILENAME
    return candidate


PLOTTING_TEMPLATE_PATH = resolve_plotting_template_path()


PLOTTING_OUTPUT_SUFFIX = "_PLOTTING"
PLOTTING_SAVE_SUFFIX = "_P"
PLOTTING_CACHE_KEY = "plotting_report"


COMMON_REPORT_FIELD_ORDER = (
    ("manufacturer", "Manufacturer"),
    ("vehicle", "Vehicle"),
    ("speed", "Speed"),
    ("test_date", "Test Date"),
    ("test_id", "Test ID"),
)


GRAPH_LAYOUT = {
    "title_box": (0.6, 0.3, 11.8, 0.45),
    "common_box": (0.6, 0.8, 11.8, 0.7),
    "graph_box": (0.6, 1.65, 8.1, 5.0),
    "injury_box": (8.95, 1.65, 3.3, 5.0),
}

