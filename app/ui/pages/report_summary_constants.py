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
    "Time: 단일 시점은 t, 구간 값은 t1 ~ t2 형식으로 표시"
)

SUMMARY_TABLE_COLUMNS = ("slot", "dummy", "region", "category", "value", "unit", "time", "limit", "status", "uid")
SUMMARY_TABLE_COLUMN_SPECS = (
    ("slot", "Slot", 60),
    ("dummy", "Dummy", 160),
    ("region", "Injury/Region", 105),
    ("category", "Category", 230),
    ("value", "Value", 90),
    ("unit", "Unit", 70),
    ("time", "Time", 130),
    ("limit", "Limit", 90),
    ("status", "Status", 80),
    ("uid", "Result UID", 290),
)

TREE_STATUS_TAG_COLORS = {
    "PASS": "#166534",
    "FAIL": "#b91c1c",
    "MISSING": "#6b7280",
    "N/A": "#1f2937",
}

STATUS_READY = "Summary report is ready."
LOADED_VALUES_INITIAL = "Loaded injury values: 0"
LOADED_VALUES_WAITING = "Loaded injury values: waiting for Valuation"
LOADED_VALUES_COUNT = "Loaded injury values: {loaded_rows} / {total_rows}"
STATUS_LOADED_SAVED = "Loaded saved summary report results."
STATUS_LOAD_DATASET_FIRST = "Load a dataset first."
STATUS_WAITING = "SUMMARY REPORT is waiting. Click Valuation to load uid-based results."
STATUS_NO_ROWS = "No summary rows are available for the selected regulation."
STATUS_NO_NUMERIC_VALUES = (
    "Stored uid results were found, but no numeric values are currently extractable for the selected regulation."
)
STATUS_VALUATION_REFRESHED = "Valuation refreshed from existing uid-based saved results."

DIALOG_TITLE_REPORT = "REPORT"
WARNING_LOAD_DATA_FIRST_KO = "먼저 데이터를 로드하세요."
WARNING_REPORT_SAVE_PATH_KO = "REPORT 저장 경로를 만들 수 없습니다."
WARNING_VALUATION_REQUIRED_KO = "먼저 Valuation으로 SUMMARY REPORT 결과를 불러오세요."

HISTORY_SUMMARY_SAVED = "Summary report saved: {display_name}"
HISTORY_SUMMARY_SAVED_DISPLAY = "Summary report saved as {display_name}"
STATUS_REPORT_SAVED = "Saved report dataset: {saved_path}"
INFO_REPORT_SAVED_KO = "REPORT 데이터가 저장되었습니다.\n{saved_path}"

STATUS_EXCEL_EXPORT_FAILED = "Excel export failed: {error}"
WARNING_EXCEL_EXPORT_FAILED = "Excel export failed.\n{error}"
INFO_EXCEL_EXPORT_COMPLETED = "Excel export completed.\nSaved to: {output_path}"
STATUS_EXCEL_EXPORT_COMPLETED = "Excel export completed. | Saved to: {output_path}"
WARNING_EXCEL_OPEN_FAILED = (
    "Excel export completed, but the file could not be opened.\n"
    "Saved to: {path}\n"
    "{error}"
)
