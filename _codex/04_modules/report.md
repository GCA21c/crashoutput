# Report module

## SUMMARY REPORT code paths
- UI table and save/restore: `app/ui/pages/report_summary_page.py`
- Snapshot builder and payload extraction: `app/report/mapping.py`
- Regulation item order and labels: `app/report/regulations/fmvss208.py`
- Injury payload source: `app/ui/pages/injury_page.py` `_build_report_values()` and `_enrich_payload_with_structured_results()`
- Excel export writer: `app/report/excel_export.py`
- Excel export aliases/template constants: `app/report/excel_summary_mapping.py`
- Excel template: `resources/templates/FMVSS208 Sumy_temp.xlsx`

## Row definition model
SUMMARY REPORT rows are driven by ordered item specs in the selected regulation module.
For FMVSS 208, edit `FMVSS_208_ITEMS` in `app/report/regulations/fmvss208.py`.

Each item defines:
- `result_key`: stable report row id, e.g. `chest.vc_sae_j1727_cfc600`
- `label`: user-facing Criteria text
- `module_key`: dummy factor module used for limits
- `section_key`: injury saved-results section, e.g. `head`, `neck`, `chest`, `pelvis`
- `value_key`: first payload key to read
- `payload_aliases`: fallback nested keys, e.g. `vc_sae_peak.value`
- `unit`: display unit
- `limit_key` or `limit_value`: optional PASS/FAIL reference
- `value_transform`: optional display/evaluation transform such as `abs`

`app/report/mapping.py` adds `region` to each row. If an item does not provide an explicit
`region`, the report uses `section_key.upper()`, so `head` becomes `HEAD` and `pelvis`
becomes `PELVIS`.

## Output order
SUMMARY REPORT is grouped by dummy slot first, then by the selected regulation item tuple.
For FMVSS 208, `FMVSS_208_ITEMS` is currently organized by injury region:
HEAD, NECK, CHEST, PELVIS, FEMUR, KNEE.

To place a new criteria row at a specific visual position inside each dummy group, insert
the `_item(...)` at that position in the tuple. For example, the CHEST V*C rows are placed
immediately after `Chest Deflection Peak`.

Acceleration-based 3ms rows should keep this order when all values are available:
1. `One Peak 3ms`
2. `Multiple Peak 3ms`
3. existing resultant/acceleration 3ms criteria, such as `Resultant Acc. 3ms Clip`
   or `Chest Acc. 3ms Clip`

## Payload key mapping
SUMMARY REPORT reads values through `app/report/mapping.py` `_extract_metric_value()`.
The lookup order is:
1. `report_values`
2. `structured_metrics`
3. top-level slot payload

For new injury values, prefer adding a stable scalar in `injury_page.py`
`_build_report_values()` and then use that scalar as the regulation item's `value_key`.
Use `payload_aliases` for existing nested structured metrics or backwards-compatible
saved files.

Examples:
- CHEST `V*C SAE J1727_CFC600`
  - `value_key`: `vc_sae_peak_mps`
  - fallback: `vc_sae_peak.value`
- PELVIS `Multiple Peak 3ms_Clip`
  - `value_key`: `pelvis_multiple_3ms_clip`
  - fallback: `multiple_peak_3ms.value`

## Adding a SUMMARY REPORT item
1. Confirm the injury calculation already stores the value in `injury_saved_results`.
2. If needed, add only a report scalar in `injury_page.py` `_build_report_values()`.
   Do not change the calculation engine for report-only additions.
3. Add an `_item(...)` entry to the regulation module in the desired output order.
4. Set `payload_aliases` for nested or legacy payload keys.
5. If the Excel template uses a different text label, add the template label alias in
   `app/report/excel_summary_mapping.py` `SUMMARY_CRITERIA_ALIASES`.
6. Run a snapshot check against representative metadata and verify the table row source
   is not `missing`.
7. Update this document or the related change log when the report structure changes.

## Excel export
`REPORT - SUMMARY` uses the `EXCEL EXPORT` button to export the current summary snapshot
into `resources/templates/FMVSS208 Sumy_temp.xlsx`.

The export flow is:
1. `report_summary_page.py` ensures `Valuation` has populated `_snapshot`.
2. The export file is saved to the application execution folder.
3. `app/report/excel_export.py` opens the template workbook with `openpyxl`.
4. Metadata fields are found by anchor labels and written to the merged cell immediately
   to the right of the label:
   - `manufacturer` -> `vehicle manufacture`
   - `vehicle` -> `vehicle model`
   - `speed` -> `test speed`
   - `test_date` -> `test date`
   - `test_id` -> `test id`
5. The injury table header row is detected by `IARV` and `RESULT` labels.
6. Each template criteria row is matched by `region + criteria label`; aliases live in
   `app/report/excel_summary_mapping.py`.
7. Only the IARV and RESULT cells are assigned values. Injury numeric values are rounded
   to two decimal places at export time with `ROUND_HALF_UP`, then written with exactly
   two decimal digits such as `0.10` or `1.00`.
8. FMVSS 208 IARV exclusions are applied by `EXCEL_IARV_EXPORT_RULES`; excluded IARV
   cells are left blank while RESULT is still exported.
9. Excel-only value transforms are applied by `EXCEL_VALUE_EXPORT_RULES`. FMVSS 208
   exports CHEST `V*C SAE J1727_CFC600` and `V*C ECE94_CFC180` RESULT values as
   positive values without changing SUMMARY REPORT screen values or calculation payloads.
10. Excel RESULT source overrides are applied by `EXCEL_RESULT_SOURCE_OVERRIDES`.
   FMVSS 208 template rows `HEAD / Resultant Acc. 3ms Clip` and
   `CHEST / Chest Acc. 3ms Clip` export the SUMMARY REPORT `Multiple Peak 3ms`
   value while keeping the template row label unchanged.
11. Fonts, fills, borders, alignment,
   row heights, column widths, merges, and formulas are not modified by the exporter.

The current template has two occupant column groups:
- first slot: `IARV` / `RESULT`
- second slot: `IARV` / `RESULT`

If a SUMMARY REPORT has more slots than the template has occupant groups, extra slots are
skipped and reported in the export result message.

Export filename rule:
- base name: template stem with a trailing `_temp` removed
- suffix: sanitized `Test ID`
- extension: template extension
- example: `FMVSS208 Sumy_ABC123.xlsx`
- empty Test ID: `NO_TEST_ID`
- duplicate filenames: append `_01`, `_02`, etc.

After the completion dialog is acknowledged, the UI opens the saved workbook with the OS
default file association. Windows uses `os.startfile`; macOS and Linux use `open` and
`xdg-open` fallbacks.
