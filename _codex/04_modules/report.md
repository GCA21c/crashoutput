# Report module

## SUMMARY REPORT code paths
- UI table and save/restore: `app/ui/pages/report_summary_page.py`
- Snapshot builder and payload extraction: `app/report/engine.py`
- Rule registry and choices: `app/report/registry.py`
- Regulation item order and labels: `app/report/rules/fmvss208.py`
- Injury payload source: `app/ui/pages/injury_page.py` `_build_report_values()` and `_enrich_payload_with_structured_results()`
- Excel export writer: `app/report/exporters/excel.py`
- Excel export runtime helpers: `app/report/exporters/runtime.py`
- Excel export aliases/template constants: `app/report/templates/fmvss208_summary.py`
- Excel template: `resources/templates/FMVSS208 Sumy_temp.xlsx`

## Naming and compatibility contract
The report module must keep user-facing labels, page keys, rule keys, template keys,
and saved metadata keys separate.

Current stable names:
- report rule key: `fmvss208`
- report rule label: `FMVSS 208`
- Excel template spec key: `fmvss208_summary`
- saved report metadata key: `report_saved_results.summary_report`
- injury result source key: `injury_saved_results`
- dummy setup metadata key: `shared_dummy_config`

Compatibility names that must remain valid until all existing saved files and imports are
migrated:
- `dummyset` page key aliases to `test_setup` in `app/shell.py`
- `DummySetPage` imports alias to `TestSetupPage` in `app/ui/pages/dummy_set_page.py`
- `report_ploting` and `ReportPlotingPage` are legacy typo-compatible identifiers; do not
  remove or rename them without adding an alias layer first
- `report_plotting` may be accepted as a forward alias, but `report_ploting` remains the
  registered page key until saved references and imports are migrated

New report rules should use a lowercase compact machine key and a regulation-style display
label. New template specs should use `{rule_key}_summary` unless there is a specific reason
to split templates by body style or output target.

## Row definition model
SUMMARY REPORT rows are driven by ordered item specs in the selected regulation module.
For FMVSS 208, edit `FMVSS_208_ITEMS` in `app/report/rules/fmvss208.py`.

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

`app/report/engine.py` adds `region` to each row. If an item does not provide an explicit
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
SUMMARY REPORT reads values through `app/report/engine.py` `_extract_metric_value()`.
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
  - `value_key`: `vc_sae_max_mps`
  - fallback: `vc_sae_max.value`
- PELVIS `Multiple Peak 3ms_Clip`
  - `value_key`: `pelvis_multiple_3ms_clip`
  - fallback: `multiple_peak_3ms.value`

Existing payload keys are compatibility contract. Do not rename saved keys in place.
For cleanup, add a new canonical key only after the old key is still read through
`payload_aliases` or a migration adapter. The table row `result_key` is the preferred
stable report identifier for new code.

## Adding a SUMMARY REPORT item
1. Confirm the injury calculation already stores the value in `injury_saved_results`.
2. If needed, add only a report scalar in `injury_page.py` `_build_report_values()`.
   Do not change the calculation engine for report-only additions.
3. Add an `_item(...)` entry to the regulation module in the desired output order.
4. Set `payload_aliases` for nested or legacy payload keys.
5. If the Excel template uses a different text label, add the template label alias in
   `app/report/templates/fmvss208_summary.py` `SUMMARY_CRITERIA_ALIASES`.
6. Run a snapshot check against representative metadata and verify the table row source
   is not `missing`.
7. Update this document or the related change log when the report structure changes.

## Excel export
`REPORT - SUMMARY` uses the `EXCEL EXPORT` button to export the current summary snapshot
into `resources/templates/FMVSS208 Sumy_temp.xlsx`.

The export flow is:
1. `report_summary_page.py` ensures `Valuation` has populated `_snapshot`.
2. `app/report/exporters/runtime.py` resolves the output filename, execution folder,
   duplicate filename, and OS file-open behavior.
3. The export file is saved to the application execution folder.
4. `app/report/exporters/excel.py` uses `openpyxl` to inspect anchors, write values to
   existing template cells, and save the workbook. The exporter does not patch worksheet
   XML directly because that can leave stale workbook internals such as `calcChain.xml`.
5. Metadata fields are found by anchor labels and written to the merged cell immediately
   to the right of the label:
   - `manufacturer` -> `vehicle manufacture`
   - `vehicle` -> `vehicle model`
   - `speed` -> `test speed`
   - `test_date` -> `test date`
   - `test_id` -> `test id`
6. Occupant labels are written from TEST SETUP slot metadata:
   - first slot -> `C9`
   - second slot -> `G9`
   - format: `{dummy_name} - {dummy_profile}`, e.g. `DRV - H3_5%F`
7. The injury table header row is detected by `IARV` and `RESULT` labels.
8. Each template criteria row is matched by `region + criteria label`; aliases live in
   `app/report/templates/fmvss208_summary.py`.
9. Only target cells are assigned values. Injury numeric values are rounded
   to two decimal places at export time with `ROUND_HALF_UP`, then written with exactly
   two decimal digits such as `0.10` or `1.00`.
10. FMVSS 208 IARV exclusions are applied by `EXCEL_IARV_EXPORT_RULES`; excluded IARV
   cells are left blank while RESULT is still exported.
11. Excel-only value transforms are applied by `EXCEL_VALUE_EXPORT_RULES`. FMVSS 208
   currently does not force CHEST V*C RESULT values positive; V*C rows export the same
   MAX value selected by SUMMARY REPORT.
12. Excel RESULT source overrides are applied by `EXCEL_RESULT_SOURCE_OVERRIDES`.
   FMVSS 208 template rows `HEAD / Resultant Acc. 3ms Clip` and
   `CHEST / Chest Acc. 3ms Clip` export the SUMMARY REPORT `Multiple Peak 3ms`
   value while keeping the template row label unchanged.
13. Fonts, fills, borders, alignment, row heights, column widths, merges, number formats,
   and formulas are not intentionally modified by the exporter. `openpyxl` may remove
   stale calculation-chain metadata during save so Excel can recalculate cleanly.

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
- export folder: executable folder for packaged runs, repository root for source runs.
  If that folder is not writable, the exporter falls back to the user's Documents folder.
  It must not use the process current working directory because Windows shortcuts may set
  it to `C:\Windows\System32`.

After the completion dialog is acknowledged, the UI opens the saved workbook with the OS
default file association. Windows uses `os.startfile`; macOS and Linux use `open` and
`xdg-open` fallbacks.

## Snapshot regression check
Before and after report refactors, compare the output of `app/report/engine.py`
`build_report_snapshot(metadata, regulation_name)`.

The minimum fields that must remain identical for a no-behavior-change refactor are:
- `regulation_name`
- slot order and each slot's `slot`, `dummy_name`, `dummy_profile`
- row count and row order
- each row's `slot`, `result_key`, `region`, `label`, `unit`
- each row's `value`, `limit`, `status`, `comparison`
- each row's `value_source`, `value_path`, `limit_source`

For Excel export refactors, also compare:
- generated output filename for the same template and Test ID
- occupant labels resolved for slot 1 and slot 2
- criteria alias matches
- IARV exclusion decisions
- RESULT source override decisions

Formatting-only differences should not change snapshot numeric values. Excel-only
rounding is checked at export time and must not be pushed back into the report snapshot.

## Phase 3 helper refactor gate
Phase 3 helper commonization must start with snapshot comparison, not code movement.

Required baseline artifacts:
- metadata with `injury_saved_results`
- `build_report_snapshot(metadata, regulation_name)` output
- saved `report_saved_results.summary_report` payload if `_R` reload behavior is in scope
- Excel export output values if template/export helper behavior is in scope

No-behavior-change helper refactors must keep these report fields identical:
- `regulation_name`
- slot count/order and each slot's `slot`, `dummy_name`, `dummy_profile`
- row count/order
- each row's `slot`, `slot_label`, `dummy_name`, `dummy_profile`
- each row's `section_key`, `region`, `result_key`, `label`
- each row's `value`, `unit`, `limit`, `status`, `comparison`
- each row's `result_uid`, `value_source`, `value_path`, `limit_source`

If saved report payload behavior is in scope, these must also remain identical:
- `report_type`
- `regulation`
- `report_fields`, including `occupant_slots`
- `slots`
- `rows`
- `excel_mapping`

First permitted Phase 3 implementation candidate:
- occupant slot merge / label extraction helper.

Rules for that first move:
- keep `report_summary_page.py` wrapper methods until user testing passes
- compare `_report_fields()` output before and after
- verify Excel occupant labels for the first and second slots
- do not change `shared_dummy_config`, `report_saved_results.summary_report`, or row payload keys

Blocked until later explicit approval:
- peak helpers
- force/moment unit conversion
- `_gradient_contiguous`
- filtering math
- derived channel generation
- injury input resolver behavior

## Occupant helper usage map
REPORT currently has multiple occupant-related paths that must not be merged in one step.

`app/ui/pages/report_summary_page.py`:
- `_occupant_slots_from_config(config)` extracts `slot`, `dummy_name`, and `dummy_profile`
  from TEST SETUP style config.
- `_merge_occupant_slots(*slot_groups)` preserves first-seen slot order and fills missing
  `dummy_name` / `dummy_profile` from later groups.
- `_report_fields()` defines the REPORT SUMMARY occupant precedence:
  1. current shared dummy config
  2. metadata `shared_dummy_config`
  3. saved `report_fields.occupant_slots`
  4. current snapshot `slots`
  5. saved summary `slots`

`app/report/exporters/excel.py`:
- `_occupant_label(slot_info)` formats `{dummy_name} - {dummy_profile}`.
- `_occupant_slot_infos(snapshot, report_fields)` builds Excel occupant labels from
  `report_fields.occupant_slots`, snapshot slots, and snapshot rows.
- `_dummy_name_from_slot_label()` is an Excel fallback when row dummy name is missing.
- `_occupant_input_cells()` finds the template targets such as C9 and G9.

`app/report/engine.py`:
- `_slot_identity()` builds snapshot slot labels and dummy display values.
- This is report snapshot contract-adjacent and should not move in early Phase 3.

First safe implementation:
- create `app/report/occupants.py`
- move only pure slot helper logic used by `report_summary_page.py`
- keep page wrappers during the first move
- leave Excel exporter and report engine occupant logic unchanged

Required verification for the first move:
- `_report_fields()` output matches before and after
- `report_fields.occupant_slots` order and values match
- Excel occupant labels for C9 and G9 remain unchanged
- `_R` reload keeps the same report input and occupant slot values

Phase 3-C implementation status:
- `app/report/occupants.py` now owns:
  - `normalize_slot_key()`
  - `occupant_slots_from_config()`
  - `merge_occupant_slots()`
- `report_summary_page.py` keeps wrapper methods and still owns `_report_fields()`.
- Excel exporter occupant fallback and report engine slot identity remain unchanged.

Phase 3-D implementation status:
- `app/report/occupants.py` also owns:
  - `occupant_label()`
  - `dummy_name_from_slot_label()`
- `app/report/exporters/excel.py` keeps wrapper functions and delegates to shared helpers.
- `_occupant_slot_infos()` remains in the Excel exporter and is not refactored yet.
- `_occupant_input_cells()` and C9/G9 target selection remain unchanged.

Phase 3-E implementation status:
- `_occupant_slot_infos()` remains in the Excel exporter.
- Its final merge now uses `merge_occupant_slots()`.
- The source order stays `report_fields.occupant_slots`, snapshot `slots`, then snapshot `rows`.
- `_occupant_input_cells()` and C9/G9 target selection remain unchanged.

Phase 3-F implementation status:
- `occupant_slot_infos_from_snapshot()` now lives in `app/report/occupants.py`.
- Excel `_occupant_slot_infos()` remains as a wrapper for rollback and delegates to that helper.
- `_occupant_input_cells()` and C9/G9 target selection remain unchanged.

Phase 3-G/H implementation status:
- `report_fields_from_sources()` now lives in `app/report/occupants.py`.
- `ReportSummaryPage._report_fields()` remains the page-level entry point and delegates report field
  assembly to the shared helper.
- REPORT SUMMARY occupant slot precedence remains current config, metadata config, saved report fields,
  current snapshot slots, then saved summary slots.
- Excel exporter no longer keeps unused wrappers for slot normalization and slot-label dummy-name
  extraction; the active Excel wrappers for occupant label and slot info remain.
