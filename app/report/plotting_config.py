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
