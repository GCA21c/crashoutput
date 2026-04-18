"""Presentation constants for the REPORT SUMMARY page."""

PAGE_TITLE = "REPORT - SUMMARY"
REGULATION_MODE_LABEL = "평가모드"

BUTTON_VALUATION = "Valuation"
BUTTON_SAVE = "Save"
BUTTON_EXCEL_EXPORT = "EXCEL EXPORT"

INPUT_GROUP_TITLE = "Report Inputs"
INFO_GROUP_TITLE = "Selected Regulation"
LOADED_GROUP_TITLE = "Loaded Injury Values"
TABLE_GROUP_TITLE = "SUMMARY REPORT"

REPORT_INPUT_FIELDS = (
    ("Manufacturer", "manufacturer"),
    ("Vehicle", "vehicle"),
    ("Speed", "speed"),
    ("Test DATE", "test_date"),
    ("Test ID", "test_id"),
)

SELECTED_REGULATION_FIELDS = (
    ("Regulation", "regulation"),
    ("Manufacturer", "manufacturer"),
    ("Vehicle", "vehicle"),
    ("Speed", "speed"),
    ("Test DATE", "test_date"),
    ("Test ID", "test_id"),
)

SUMMARY_GUIDE_TEXT = (
    "Status: PASS=limit 만족, FAIL=limit 초과, MISSING=저장된 결과값 없음, N/A=비교 limit 없음 | "
    "Source: Saved value=uid 결과 payload에 구조화된 수치가 저장되어 그 값을 직접 읽음"
)

SUMMARY_TABLE_COLUMNS = ("slot", "dummy", "region", "criterion", "value", "unit", "limit", "status", "uid", "source")
SUMMARY_TABLE_COLUMN_SPECS = (
    ("slot", "Slot", 60),
    ("dummy", "Dummy", 160),
    ("region", "Injury/Region", 105),
    ("criterion", "Criteria", 230),
    ("value", "Value", 90),
    ("unit", "Unit", 70),
    ("limit", "Limit", 90),
    ("status", "Status", 80),
    ("uid", "Result UID", 290),
    ("source", "Source", 90),
)

TREE_STATUS_TAG_COLORS = {
    "PASS": "#166534",
    "FAIL": "#b91c1c",
    "MISSING": "#6b7280",
    "N/A": "#1f2937",
}

SOURCE_DISPLAY_NAMES = {
    "report_values": "Saved value (report_values)",
    "structured_metrics": "Saved value (structured_metrics)",
    "top_level": "Saved value (top-level payload)",
}

STATUS_READY = "Summary report is ready."
LOADED_VALUES_INITIAL = "Loaded injury values: 0"
LOADED_VALUES_WAITING = "Loaded injury values: waiting for Valuation"
STATUS_LOADED_SAVED = "Loaded saved summary report results."
STATUS_LOAD_DATASET_FIRST = "Load a dataset first."
STATUS_WAITING = "SUMMARY REPORT is waiting. Click Valuation to load uid-based results."
STATUS_NO_ROWS = "No summary rows are available for the selected regulation."
STATUS_NO_NUMERIC_VALUES = (
    "Stored uid results were found, but no numeric values are currently extractable for the selected regulation."
)
STATUS_VALUATION_REFRESHED = "Valuation refreshed from existing uid-based saved results."
