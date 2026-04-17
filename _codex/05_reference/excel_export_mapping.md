# Excel export mapping

## Template
- Path: `resources/templates/FMVSS208 Sumy_temp.xlsx`
- Writer: `app/report/excel_export.py`
- Mapping constants: `app/report/excel_summary_mapping.py`
- Runtime dependency: `openpyxl`

## Metadata anchors
The exporter searches normalized label text and writes to the merged/input cell immediately
to the right of the label range.

| Report field | Template anchor |
|---|---|
| `manufacturer` | `vehicle manufacture` |
| `vehicle` | `vehicle model` |
| `speed` | `test speed` |
| `test_date` | `test date` |
| `test_id` | `test id` |

## Injury table detection
- Header row is detected by cells whose normalized text is `IARV` and `RESULT`.
- Each occupant group is the nearest `RESULT` column to the right of an `IARV` column.
- The current template supports two occupant groups.
- Criteria rows are matched by `region + criteria label`.
- IARV receives the SUMMARY REPORT `limit` value.
- RESULT receives the SUMMARY REPORT `value`.
- Missing values are written as blank cells.
- Injury numeric values are rounded at export time to two decimal places with
  `Decimal(..., ROUND_HALF_UP)`.

## FMVSS 208 IARV exclusions
Maintain regulation-aware IARV exclusions in `app/report/excel_summary_mapping.py`
`EXCEL_IARV_EXPORT_RULES`.

For `FMVSS 208`, these IARV cells are intentionally left blank because the current FMVSS
summary template has no applicable IARV basis for them:

| Region | SUMMARY REPORT criteria |
|---|---|
| `HEAD` | `HIC36ms` |
| `HEAD` | `Resultant Acc. 3ms Clip` |
| `NECK` | `Peak Extension MOCy` |
| `NECK` | `Peak Flexion MOCy` |

The RESULT cells for the same rows are still exported when values are available.

## Criteria aliases
Template labels do not always match SUMMARY REPORT labels exactly. Maintain aliases in
`app/report/excel_summary_mapping.py` `SUMMARY_CRITERIA_ALIASES`.

Examples:
- `HEAD / HIC 15ms` -> `HIC15ms`
- `NECK / MOCy - Peak Extension` -> `Peak Extension MOCy`
- `CHEST / Chest Def.` -> `Chest Deflection Peak`
- `CHEST / Chest V*C - SAE J1727` -> `V*C SAE J1727_CFC600`
- `FEMUR / Left Femur Force` -> `Left Peak Axial Force`
- `KNEE / Left Knee Disp.` -> `Left KNEE Displacement Peak`

## Template style rule
The exporter opens the template workbook and assigns values only. It must not:
- change row heights or column widths
- merge or unmerge cells
- alter fonts, fills, borders, or alignment
- overwrite formulas outside the IARV/RESULT targets
- create a new workbook from scratch

When the template changes, re-run the workbook anchor inspection and update only the alias
or detection helpers needed for the new labels.

## Save and open rule
- Output folder: application execution folder.
- Filename: `{template_stem}_{sanitized_test_id}{template_suffix}`.
- Empty Test ID fallback: `NO_TEST_ID`.
- Duplicate names are auto-incremented with `_01`, `_02`, etc.
- Completion popup contains only:
  - `Excel export completed.`
  - `Saved to: <path>`
- After the user confirms the popup, the UI opens the saved workbook with the OS default
  application. Open failure does not invalidate the export.
