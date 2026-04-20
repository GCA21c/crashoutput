# Refactor phase tracker

이 문서는 현재 리팩토링 진행 위치를 기록한다.
다음 작업을 시작하기 전 항상 이 문서를 확인한다.

## Current branch
- `코드최적화p5`

## Global guard
- 계산 로직 변경 금지
- 현재 phase가 명시적으로 완료되기 전 다음 phase 시작 금지
- 사용자 테스트 결과 확인 전 phase 완료 선언 금지
- key / file / class rename은 alias 유지 없이는 금지

## Phase status
| Phase | Status | Notes |
|---|---|---|
| Quick Win | Done | report contract docs, Excel runtime helper, snapshot regression notes |
| Phase 1-A | Done | naming reference search / contract check |
| Phase 1-B | Partial | PLOTING user-facing label changed to PLOTTING; no key/class/file rename |
| Phase 1-C | Done | user tested overall startup/navigation; aliases documented and kept; no key/class/file rename |
| Phase 1-D | Done | rename candidate list documented; no code rename |
| Phase 1-E | Done | user accepted deferring actual internal key/class/file renames |
| Phase 1 | Closed | user tested overall program as normal after Phase 1 |
| Phase 2-A | Done | user tested normal startup/navigation after shared UI style constants split |
| Phase 2-B | Done | user tested report summary presentation constants split |
| Phase 2-C | Done | user tested report summary message/status constants split |
| Phase 2-D | Done | user tested report summary dialog helper wrappers |
| Phase 2-E | Done | user tested report summary loaded-count display helper |
| Phase 2-F | Done | user tested report summary input variable helper reuse |
| Phase 2-G | Done | user tested report summary valuation status helper |
| Phase 2-H | Done | user tested report summary Excel export success helper |
| Phase 2-I | Done | final whole-program user test passed; closure boundary documented |
| Phase 2 | Closed | low-risk split complete and user-tested |
| Phase 3-A | Done | snapshot comparison criteria reviewed; no code changes |
| Phase 3-B | Done | occupant helper usage analysis reviewed; no code changes |
| Phase 3-C | Done | user tested first occupant helper extraction |
| Phase 3-D | Done | user tested Excel occupant label helper reuse |
| Phase 3-E | Done | user tested Excel occupant slot merge helper reuse |
| Phase 3-F | Done | user tested Excel occupant slot info wrapper |
| Phase 3-G | Done | user tested REPORT SUMMARY report field assembly helper |
| Phase 3-H | Done | user tested unused Excel occupant wrapper cleanup |
| Phase 3-I | Done | user tested REPORT SUMMARY occupant wrapper closure |
| Phase 3-J | Done | Phase 3 closure boundary documented; calculation-adjacent helpers deferred |
| Phase 3 | Closed | occupant helper commonization complete and user-tested |
| Phase 4-A | Done | user tested REPORT SUMMARY payload/cache orchestration service |
| Phase 4-B | Done | user tested DATA FILTERING AUTO SET matching service |
| Phase 4-C | Done | user tested shell persistence metadata helper |
| Phase 4-D | Done | user tested injury derived-channel lookup helper and Index fix |
| Phase 4-E | Done | user tested REPORT SUMMARY Excel export service route |
| Phase 4-F | Done | user tested DATA FILTERING apply-map normalization/status helpers |
| Phase 4-G | Done | user tested DATA FILTERING commit rename/summary pure helpers |
| Phase 4-H | Done | user tested DATA FILTERING commit payload helper and OFFSET preview fixes |
| Phase 4-I | Done | Phase 4 closure boundary documented; high-risk moves deferred |
| Phase 4 | Closed | orchestration split complete and user-tested |
| Phase 5-A | Partial | regression snapshot tool/docs added; actual baseline JSON requires representative saved `.pkl` |
| Phase 5-B | Done | preprocessing function groups and folder-level snapshot compare workflow verified |
| Phase 5-C | Done | channel role detector helper extraction implemented and user-tested |
| Phase 5-D | Done | numeric/time helper extraction implemented and user-tested |
| Phase 5-E | Done | offset/trimming helper extraction implemented and user-tested |
| Phase 5-F | Done | viewer/channel search helper extraction implemented and user-tested |
| Phase 5-G | Partial | filter source helper extraction implemented; awaiting user runtime test |
| Phase 5 | In Progress | Started with regression fixture tooling only |

## Completed work on this branch
- Added `app/report/exporters/runtime.py`.
- Moved Excel export runtime helpers out of `app/ui/pages/report_summary_page.py`.
- Documented report naming / compatibility contract in `_codex/04_modules/report.md`.
- Documented report snapshot regression criteria in `_codex/04_modules/report.md`.
- Corrected user-facing PLOTTING labels while retaining legacy `report_ploting` identifiers.
- Added `PAGE_KEY_ALIASES` in `app/shell.py`.
- Documented `dummyset` and `DummySetPage` compatibility requirements.

## Current next action
Wait for user runtime test after Phase 5-G filter source helper extraction.

Phase 5-A scope:
- Added `tools/capture_regression_snapshot.py`.
- Added `_codex/03_workflows/regression_snapshot_workflow.md`.
- Added `_codex/09_regression_snapshots/README.md`.
- Added `_codex/09_regression_snapshots/input_files/` for local representative `.pkl` inputs.
- Generated local baseline snapshots from a 2-dummy H3_5%F dataset:
  - `_O`
  - `_O_F`
  - `_O_F_T`
  - `_O_F_T_I`
  - `_O_F_T_I_R`
- No calculation logic, filtering math, injury formula, report extraction key, or pickle format change.
- Snapshot JSON files are local/ignored by git by default.

Phase 5-B scope:
- Added folder-level `capture-dir` and `compare-dir` commands to `tools/capture_regression_snapshot.py`.
- Added `_codex/04_modules/preprocessing.md` to classify `app/services/preprocessing/service.py`
  function groups and extraction risk.
- Added `_codex/09_regression_snapshots/before/` and `after/` placeholder folders.
- Verified `capture-dir` and `compare-dir` with the 5 representative H3_5%F two-dummy files.
- Still no function movement, no calculation logic change, and no app runtime path change.

Phase 5-C scope:
- Added `app/services/preprocessing/channel_roles.py`.
- Moved pure string-based channel role detection and derived-channel naming helpers out of
  `app/services/preprocessing/service.py`.
- `service.py` imports the moved names to preserve existing import paths.
- Verified Phase 5 snapshot compare loop after the move: all 5 representative snapshots match.
- User tested runtime behavior as normal after the move.
- Did not move `apply_filtering_with_derivatives()`, `apply_filtering()`, CFC filter kernel,
  End Points extension, HIC/3ms/VC/Nij/femur calculation functions.

Phase 5-D scope:
- Added `app/services/preprocessing/timing.py`.
- Moved numeric channel, time numeric, Time0 row, and sample-rate helpers out of
  `app/services/preprocessing/service.py`.
- `service.py` keeps `_get_sample_rate` as an import alias for compatibility.
- Verified import compatibility and Phase 5 snapshot compare loop: all 5 representative snapshots match.
- User tested runtime behavior as normal after the move.
- Did not move trimming/offset commit functions, filtering functions, CFC filter kernel,
  End Points extension, HIC/3ms/VC/Nij/femur calculation functions.

Phase 5-E scope:
- Added `app/services/preprocessing/offset.py`.
- Added `app/services/preprocessing/series_ops.py`.
- Moved trim, offset sample-row, offset apply, and shared numeric series write helpers out of
  `app/services/preprocessing/service.py`.
- `service.py` keeps `trim_dataframe`, `get_offset_sample_rows`, `apply_offset`, and
  `_replace_with_numeric_series` import compatibility.
- Verified import compatibility and Phase 5 snapshot compare loop: all 5 representative snapshots match.
- User tested runtime behavior as normal after the move.
- Did not move filtering functions, CFC filter kernel, End Points extension,
  HIC/3ms/VC/Nij/femur calculation functions.

Phase 5-F scope:
- Added `app/services/preprocessing/channel_search.py`.
- Moved viewer-based channel search, channel grouping, resultant auto-pick, and simple injury
  auto-detection helpers out of `app/services/preprocessing/service.py`.
- `service.py` keeps `make_channel_search_text`, `infer_channel_group_key`,
  `auto_detect_injury_channels`, and `_find_resultant_or_axis` import compatibility.
- Verified import compatibility and Phase 5 snapshot compare loop: all 5 representative snapshots match.
- User tested runtime behavior as normal after the move.
- Did not move filtering functions, CFC filter kernel, End Points extension,
  HIC/3ms/VC/Nij/femur calculation functions.

DATA FILTERING display prefix scope:
- Added DAT load-time display-order metadata in `app/services/io/dat_loader.py`.
- DATA FILTERING list rows may display `002:B1:` style prefixes through `app/ui/pages/filtering_page.py`.
- Prefixes are display-only and are not written into dataframe column names, ISO rewrite keys,
  filter-label keys, descriptions, units, derived-channel keys, report payloads, or saved injury data.
- DAT sample `1.zip` confirmed Time=`001` and the first data channel=`002` using DAT header block order.
- Existing saved `.pkl` regression snapshots still match because this display metadata is absent from
  older saves and falls back to view-only dataframe order.
- Fixed a DATA FILTERING display fallback crash caused by evaluating a pandas `Index` as a boolean.
- User tested the display prefix and fallback fix as normal.

Phase 5-G scope:
- Added `app/services/preprocessing/filter_sources.py`.
- Moved CFC label parsing, safe column-set conversion, root source resolution, effective time-column
  resolution, raw-aligned source extraction, and filter source-series resolution out of
  `app/services/preprocessing/service.py`.
- `service.py` keeps `parse_cfc_filter_label` and legacy private helper names available through imports.
- Verified import compatibility and Phase 5 snapshot compare loop: all 5 representative snapshots match.
- Did not move `apply_filtering_with_derivatives()`, `apply_filtering()`, CFC filter kernel,
  End Points extension, HIC/3ms/VC/Nij/femur calculation functions.

Phase 1-C decisions:
- Keep `self.pages["dummyset"] = self.pages["test_setup"]`.
- Keep `DummySetPage = TestSetupPage`.
- Keep `report_ploting` and `ReportPlotingPage` as legacy internal identifiers.
- Accept `report_plotting` only as a forward alias.
- Do not rename files or classes in Phase 1-C.
- Keep report names stable:
  - rule key: `fmvss208`
  - rule label: `FMVSS 208`
  - template key: `fmvss208_summary`

## Last known user test result
- Program starts and overall behavior is normal after Quick Win and Phase 1-B/C partial changes.
- Phase 1-C final alias/comment contract changes were user-tested as normal overall startup/navigation.
- Phase 1-E deferral decision was accepted, and the overall program was user-tested as normal.
- Phase 2-A shared UI style constants split was user-tested as normal.
- Phase 2-B report summary presentation constants split was user-tested as normal.
- Phase 2-C report summary message/status constants split was user-tested as normal.
- Phase 2-D report summary dialog helper wrappers were user-tested as normal.
- Phase 2-E report summary loaded-count display helper was user-tested as normal.
- Phase 2-F report summary input-variable helper reuse was user-tested as normal.
- Phase 2-G report summary valuation status helper was user-tested as normal.
- Phase 2-H report summary Excel export success helper was user-tested as normal.
- Phase 2 final whole-program test was completed as normal.

## Phase 1-D candidate decisions
- Keep `report_ploting` as registered internal page key.
- Keep `ReportPlotingPage` and `app/ui/pages/report_ploting_page.py` for now.
- Use `report_plotting` only as a forward alias.
- Keep `dummyset` as compatibility alias to `test_setup`.
- Keep `DummySetPage` and `dummy_set_page.py` as import shim.
- Do not rename metadata keys: `shared_dummy_config`, `injury_saved_results`, `report_saved_results.summary_report`.
- Do not rename report contract fields: `result_key`, `value_key`, `payload_aliases`.
- Do not rename report rule/template names: `fmvss208`, `FMVSS 208`, `fmvss208_summary`.
- Do not rename injury slot payload keys such as `head_metadata` and `*_saved_payload`.
- Treat `criterion_key` and `dummy_profile` as compatibility pair.

## Phase 1-E decision
- No actual internal key/class/file rename will be performed in `코드최적화p1`.
- Keep `report_ploting`, `ReportPlotingPage`, and `app/ui/pages/report_ploting_page.py`.
- Keep `dummyset`, `DummySetPage`, and `dummy_set_page.py`.
- Real rename work is deferred to a later, explicitly approved compatibility phase.
- Phase 1 is closed after user acceptance and normal program test.

## Phase 2 guard
- Phase 2 may start with low-risk split only.
- Do not touch calculation logic.
- Do not touch `apply_filtering_with_derivatives()`.
- Do not touch `_resolve_standard_series_for_calc()`.
- Do not rename metadata or payload keys.

## Phase 2-A scope
- Added `app/ui/styles.py` for shared Tk color/font constants.
- Applied the constants only to:
  - `app/shell.py`
  - `app/ui/pages/report_ploting_page.py`
- This is a UI style constant split only.
- User tested startup/navigation as normal before the next Phase 2 slice.

## Phase 2-B candidate scope
- Continue only with another low-risk separation.
- Recommended next unit: move report summary UI label/order constants that are purely presentation-level.
- Do not touch Excel writer behavior, summary payload keys, metric extraction, filtering, or injury calculation.

## Phase 2-B scope
- Added `app/ui/pages/report_summary_constants.py` for report summary presentation constants.
- Moved only UI labels, table headings, table status colors, source display names, and status strings.
- Kept `app/ui/pages/report_summary_page.py` responsible for page behavior.
- Did not change summary payload keys, report snapshot building, save/load metadata, Excel writer behavior, filtering, or injury calculation.
- User tested REPORT - SUMMARY screen rendering, Valuation button, Save button visibility, Excel Export button visibility, and saved summary reload display before the next Phase 2 slice.

## Phase 2-C scope
- Moved remaining REPORT SUMMARY messagebox/history/status text templates into `app/ui/pages/report_summary_constants.py`.
- Kept messagebox call sites, save/report/export control flow, metadata keys, and Excel writer behavior unchanged.
- User tested Save, Excel Export success, and available warning paths before the next Phase 2 slice.

## Phase 2-D scope
- Added small `_show_report_warning()` and `_show_report_info()` helpers in `app/ui/pages/report_summary_page.py`.
- Replaced direct REPORT messagebox title call sites with these helpers only.
- Kept save/export branching, metadata writes, report payload, Excel writer behavior, filtering, and injury calculation unchanged.
- User tested REPORT SUMMARY Save and Excel Export dialogs before the next Phase 2 slice.

## Phase 2-E scope
- Added `LOADED_VALUES_COUNT` to `app/ui/pages/report_summary_constants.py`.
- Added `_set_loaded_values_count()` in `app/ui/pages/report_summary_page.py`.
- Reused the helper for saved summary restore and Valuation loaded-count display.
- Kept row building, value extraction, metadata writes, Excel writer behavior, filtering, and injury calculation unchanged.
- User tested saved summary restore and Valuation loaded-count display before the next Phase 2 slice.

## Phase 2-F scope
- Reused `_report_input_variables()` for input trace registration, saved report field restore, report field serialization, and reset.
- Added `_set_report_input_values()` in `app/ui/pages/report_summary_page.py`.
- Kept report field keys, metadata structure, save/export behavior, Excel writer behavior, filtering, and injury calculation unchanged.
- User tested report input restore/reset, Save, and Excel Export before the next Phase 2 slice.

## Phase 2-G scope
- Added `_set_valuation_status()` in `app/ui/pages/report_summary_page.py`.
- Moved only the existing `run_valuation()` status message selection into that helper.
- Kept snapshot building, row population, loaded-count display, cache update, report payload, Excel writer behavior, filtering, and injury calculation unchanged.
- User tested Valuation status messages and normal REPORT SUMMARY display before the next Phase 2 slice.

## Phase 2-H scope
- Added `_handle_excel_export_success()` in `app/ui/pages/report_summary_page.py`.
- Moved only the existing Excel export success status, info dialog, and open-file call into that helper.
- Kept output path generation, Excel writer call, error handling, save/load metadata, report payload, filtering, and injury calculation unchanged.
- User tested Excel Export success dialog and automatic file open before the Phase 2 closure step.

## Phase 2-I closure boundary
- No additional code refactor is planned in Phase 2.
- Phase 2 changed only low-risk UI/presentation/runtime helper boundaries:
  - shared Tk style constants
  - REPORT SUMMARY presentation constants
  - REPORT SUMMARY message/status helpers
  - REPORT SUMMARY local helper wrappers
- Phase 2 intentionally did not change:
  - filtering math
  - injury formulas
  - report snapshot/value extraction
  - report payload keys
  - saved metadata keys
  - Excel writer internals
  - Excel template mapping rules
  - offset/trimming behavior
- Final Phase 2 user test should cover:
  - program startup
  - navigation
  - REPORT SUMMARY Valuation
  - Save and `_R` reload
  - Excel Export and automatic open
  - representative TEST SETUP / DATA FILTERING / INJURY page entry
- Do not start Phase 3 in this branch.
- Phase 3 must start only after final Phase 2 test and a new branch is created.
- Final Phase 2 whole-program user test passed.
- Phase 2 is closed.

## Phase 3 start guard
- Phase 3 code changes must happen on a new branch.
- Define snapshot comparison criteria before changing helper behavior.
- Do not touch filtering math, injury formulas, report extraction contract, payload keys, or saved metadata keys without explicit approval.

## Phase 3-A snapshot criteria
Phase 3-A is documentation-only. No code behavior is changed here.

Baseline sources:
- saved dataset metadata containing `injury_saved_results`
- report snapshot from `build_report_snapshot(metadata, regulation_name)`
- saved REPORT SUMMARY payload under `report_saved_results.summary_report`
- Excel export output values only when an export-specific refactor is in scope

Minimum report snapshot fields that must match before and after a no-behavior-change helper refactor:
- `regulation_name`
- slot count and slot order
- each slot's `slot`, `dummy_name`, `dummy_profile`
- row count and row order
- each row's `slot`, `slot_label`, `dummy_name`, `dummy_profile`
- each row's `section_key`, `region`, `result_key`, `label`
- each row's `value`, `unit`, `limit`, `status`, `comparison`
- each row's `result_uid`, `value_source`, `value_path`, `limit_source`

Minimum REPORT SUMMARY saved payload fields that must match:
- `report_type`
- `regulation`
- `report_fields` keys and values, including `occupant_slots`
- `slots`
- `rows`
- `excel_mapping`

Allowed differences:
- pure UI layout internals
- helper function location
- comments and documentation
- import location when public behavior and compatibility wrappers remain stable

Disallowed differences without explicit approval:
- numeric injury values
- report row order
- limit/status/comparison
- `result_key`, `value_key`, `payload_aliases`
- saved metadata keys
- Excel result/IARV cell values
- occupant label text such as `DRV - H3_5%F`

First Phase 3 implementation candidate:
- analyze and then move occupant slot merge / label extraction into a report helper module.
- keep wrappers in `report_summary_page.py` for rollback.
- compare `_report_fields()` output before and after the move.

Still blocked in early Phase 3:
- peak helpers
- force/moment unit conversion helpers
- `_gradient_contiguous`
- filtering math and derived channel generation
- injury input resolver behavior

## Phase 3-B occupant helper usage analysis
Phase 3-B is analysis/documentation-only. No code behavior is changed here.

Current occupant-related code paths:
- `app/ui/pages/report_summary_page.py`
  - `_occupant_slots_from_config(config)`
  - `_merge_occupant_slots(*slot_groups)`
  - `_report_fields()`
- `app/report/exporters/excel.py`
  - `_occupant_label(slot_info)`
  - `_normalize_slot_key(slot)`
  - `_dummy_name_from_slot_label(slot_label, slot)`
  - `_occupant_slot_infos(snapshot, report_fields)`
  - `_occupant_input_cells(ws, template_spec)`
- `app/report/engine.py`
  - `_shared_slot_meta(metadata)`
  - `_resolve_slots(metadata, injury_saved)`
  - `_slot_identity(slot, slot_payload, slot_meta)`
- `app/ui/pages/test_setup_page.py`
  - writes `shared_dummy_config.slot_meta`
- `app/shell.py`
  - normalizes and persists `shared_dummy_config.slot_meta`

Data precedence currently used by REPORT SUMMARY `_report_fields()`:
1. current workbench shared dummy config
2. metadata `shared_dummy_config`
3. saved `report_fields.occupant_slots`
4. current `_snapshot.slots`
5. saved summary `slots`

Data precedence currently used by Excel export occupant labels:
1. `report_fields.occupant_slots`
2. snapshot `slots`
3. snapshot `rows`
4. fallback extraction from `slot_label`

First implementation candidate:
- Add a report-level helper module, recommended path: `app/report/occupants.py`.
- Move only pure occupant slot normalization/merge/config extraction into that module first.
- Keep `report_summary_page.py` methods as wrappers during the first implementation:
  - `_occupant_slots_from_config()` calls the new helper
  - `_merge_occupant_slots()` calls the new helper
- Do not move `_report_fields()` in the first implementation.
- Do not change Excel exporter behavior in the first implementation.

Expected first helper API:
- `normalize_slot_key(slot) -> str`
- `occupant_slots_from_config(config) -> list[dict]`
- `merge_occupant_slots(*slot_groups) -> list[dict]`

First implementation verification:
- compare `_report_fields()` before/after using a config with:
  - active positions such as `B1`, `B3`
  - row positions
  - slot meta with empty and non-empty `dummy_name` / `dummy_profile`
  - saved `occupant_slots`
  - snapshot `slots`
- verify REPORT SUMMARY Save and `_R` reload
- verify Excel occupant labels for first and second slots

Deferred occupant-related moves:
- Excel `_occupant_slot_infos()` can be refactored only after the first helper move is user-tested.
- `app/report/engine.py` `_slot_identity()` is report snapshot contract-adjacent and should not move in early Phase 3.
- `_report_fields()` itself remains in the page until occupant helper stability is proven.

## Phase 3-C occupant helper extraction
- Added `app/report/occupants.py`.
- Moved only pure helper logic from `app/ui/pages/report_summary_page.py`:
  - `normalize_slot_key()`
  - `occupant_slots_from_config()`
  - `merge_occupant_slots()`
- Kept page wrapper methods:
  - `_occupant_slots_from_config()`
  - `_merge_occupant_slots()`
- Kept `_report_fields()` in the page.
- Did not change Excel exporter occupant fallback logic.
- Did not change report engine slot identity logic.
- Did not change save/load metadata keys, report payload keys, filtering, or injury calculation.
- User tested REPORT SUMMARY Save, `_R` reload, and Excel C9/G9 occupant labels before the next occupant helper refactor.

## Phase 3-D Excel occupant label helper reuse
- Added shared helpers to `app/report/occupants.py`:
  - `occupant_label()`
  - `dummy_name_from_slot_label()`
- Kept Excel exporter wrapper function names:
  - `_occupant_label()`
  - `_normalize_slot_key()`
  - `_dummy_name_from_slot_label()`
- Excel wrapper functions now delegate to `app/report/occupants.py`.
- Did not change `_occupant_slot_infos()` merge/fallback flow.
- Did not change `_occupant_input_cells()` or C9/G9 target selection.
- Did not change Excel writer value/cell behavior, report payload, metadata keys, filtering, or injury calculation.
- User tested Excel C9/G9 occupant labels and REPORT SUMMARY Save / `_R` reload before further occupant refactor.

## Phase 3-E Excel occupant slot merge helper reuse
- Excel `_occupant_slot_infos()` now delegates the final slot merge to `merge_occupant_slots()`.
- The input precedence remains:
  1. `report_fields.occupant_slots`
  2. snapshot `slots`
  3. snapshot `rows`
- Excel row fallback still extracts dummy name from `slot_label` when needed.
- `_occupant_input_cells()` and C9/G9 target selection remain unchanged.
- Report engine slot identity remains unchanged.
- Save/load metadata keys, report payload keys, filtering, and injury calculation remain unchanged.
- User tested Excel C9/G9 occupant labels and REPORT SUMMARY Save / `_R` reload before further occupant refactor.

## Phase 3-F Excel occupant slot info wrapper
- Added `occupant_slot_infos_from_snapshot()` to `app/report/occupants.py`.
- Excel `_occupant_slot_infos()` remains as a wrapper and delegates to the shared helper.
- The source precedence remains:
  1. `report_fields.occupant_slots`
  2. snapshot `slots`
  3. snapshot `rows`
- Excel row fallback still extracts dummy name from `slot_label` when needed.
- `_occupant_input_cells()` and C9/G9 target selection remain unchanged.
- Report engine slot identity remains unchanged.
- Save/load metadata keys, report payload keys, filtering, and injury calculation remain unchanged.
- User tested Excel C9/G9 occupant labels and REPORT SUMMARY Save / `_R` reload before further occupant refactor.

## Phase 3-G REPORT field assembly helper
- Added `report_fields_from_sources()` to `app/report/occupants.py`.
- `ReportSummaryPage._report_fields()` remains as the page entry point and delegates report input field / occupant slot assembly to the helper.
- The REPORT SUMMARY occupant source precedence remains:
  1. current workbench shared dummy config
  2. metadata `shared_dummy_config`
  3. saved `report_fields.occupant_slots`
  4. current snapshot `slots`
  5. saved summary `slots`
- Save/load metadata keys, report payload keys, filtering, and injury calculation remain unchanged.

## Phase 3-H Excel unused wrapper cleanup
- Removed unused Excel exporter private wrappers for slot normalization and slot-label dummy-name extraction.
- Kept `_occupant_label()` and `_occupant_slot_infos()` wrappers because they are still used by Excel export flow.
- Excel occupant source precedence, C9/G9 target selection, value writing, formatting, and template handling remain unchanged.

## Phase 3-I REPORT SUMMARY occupant wrapper closure
- Removed unused `ReportSummaryPage._occupant_slots_from_config()` and
  `ReportSummaryPage._merge_occupant_slots()` wrapper methods.
- `ReportSummaryPage._report_fields()` remains the page entry point and delegates to
  `report_fields_from_sources()`.
- REPORT SUMMARY occupant source precedence, save/load metadata keys, report payload keys,
  filtering, and injury calculation remain unchanged.
- User tested the Phase 3-I wrapper closure as normal.

## Phase 3-J closure boundary
- Phase 3 is closed after occupant helper commonization only.
- Completed common helper scope:
  - `normalize_slot_key()`
  - `occupant_slots_from_config()`
  - `merge_occupant_slots()`
  - `occupant_label()`
  - `dummy_name_from_slot_label()`
  - `occupant_slot_infos_from_snapshot()`
  - `report_fields_from_sources()`
- Kept intentionally unchanged:
  - `ReportSummaryPage._report_fields()` page entry point
  - Excel `_occupant_label()` and `_occupant_slot_infos()` active wrappers
  - Excel `_occupant_input_cells()` and C9/G9 target selection
  - `app/report/engine.py` `_slot_identity()`
- Deferred out of Phase 3 because they can affect numeric results:
  - time/value valid mask helpers
  - peak helpers
  - force/moment unit conversion helpers
  - `_gradient_contiguous`
  - filtering math and derived channel generation
