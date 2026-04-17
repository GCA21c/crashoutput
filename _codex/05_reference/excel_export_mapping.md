# Excel export mapping

## Template
- Path: `resources/templates/FMVSS208 Sumy_temp.xlsx`
- Writer: `app/report/excel_export.py`
- Mapping constants: `app/report/excel_summary_mapping.py`
- Runtime dependency: `openpyxl`
- Export writer rule: use `openpyxl` only for template inspection. Final output is a
  byte-for-byte template copy with worksheet XML cell values patched. Do not call
  `workbook.save()` for export because it can rewrite merged-cell styles.

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

## Occupant labels
The exporter writes TEST SETUP slot labels without changing cell styles:

| Slot order | Template cell | Value format |
|---|---|---|
| 1st active slot | `C9` | `{dummy_name} - {dummy_profile}` |
| 2nd active slot | `G9` | `{dummy_name} - {dummy_profile}` |

Example: `DRV - H3_5%F`.

## Injury table detection
- Header row is detected by cells whose normalized text is `IARV` and `RESULT`.
- Each occupant group is the nearest `RESULT` column to the right of an `IARV` column.
- The current template supports two occupant groups.
- Criteria rows are matched by `region + criteria label`.
- IARV receives the SUMMARY REPORT `limit` value.
- RESULT receives the SUMMARY REPORT `value`.
- Missing values are written as blank cells.
- Injury numeric values are rounded at export time to two decimal places with
  `Decimal(..., ROUND_HALF_UP)` and then written with exactly two decimal digits.
  Examples: `0.1` -> `0.10`, `1` -> `1.00`.

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

## Excel-only value transforms
Maintain export-only value transforms in `app/report/excel_summary_mapping.py`
`EXCEL_VALUE_EXPORT_RULES`.

FMVSS 208 currently does not force CHEST V*C RESULT values positive. V*C rows export
the same MAX value selected by SUMMARY REPORT.

## Excel RESULT source overrides
Maintain template-row-specific RESULT source overrides in `app/report/excel_summary_mapping.py`
`EXCEL_RESULT_SOURCE_OVERRIDES`.

For `FMVSS 208`, these Excel template rows keep their template label but export the
SUMMARY REPORT `Multiple Peak 3ms` value:

| Region | Excel template row | Export RESULT source |
|---|---|---|
| `HEAD` | `Resultant Acc. 3ms Clip` | `Multiple Peak 3ms` |
| `CHEST` | `Chest Acc. 3ms Clip` | `Multiple Peak 3ms` |

This is an Excel export rule only. SUMMARY REPORT screen rows and 3ms calculations are
not changed.

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
- save the workbook through `openpyxl`

When the template changes, re-run the workbook anchor inspection and update only the alias
or detection helpers needed for the new labels.

## Save and open rule
- Output folder: application execution folder.
- Filename: `{template_stem_without_trailing_temp}_{sanitized_test_id}{template_suffix}`.
- Example: `FMVSS208 Sumy_ABC123.xlsx` from template `FMVSS208 Sumy_temp.xlsx`.
- Empty Test ID fallback: `NO_TEST_ID`.
- Duplicate names are auto-incremented with `_01`, `_02`, etc.
- The exporter does not use `Path.cwd()` for the output folder. Windows shortcuts can
  launch the process with `C:\Windows\System32` as the current working directory, which
  causes permission errors. Packaged runs use the executable folder; source runs use the
  repository root; non-writable folders fall back to the user's Documents folder.
- Completion popup contains only:
  - `Excel export completed.`
  - `Saved to: <path>`
- After the user confirms the popup, the UI opens the saved workbook with the OS default
  application. Open failure does not invalidate the export.
