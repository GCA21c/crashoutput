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
