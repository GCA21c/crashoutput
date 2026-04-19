# Refactor master plan

이 문서는 코드 최적화 / 리팩토링의 전체 방향을 고정한다.
리팩토링 중 판단이 흔들리면 이 문서를 기준으로 phase를 확인한다.

## Global rule
- 계산 결과 불변이 최우선이다.
- 다음 phase는 현재 phase가 명시적으로 완료되고 사용자 테스트가 끝나기 전까지 시작하지 않는다.
- 실제 rename, 파일 이동, 함수 이동은 compatibility alias와 rollback 경로를 먼저 확보한 뒤 진행한다.
- 기존 pickle / metadata key는 삭제하지 않는다. 신규 key를 추가하더라도 기존 key는 adapter 또는 alias로 계속 읽는다.
- filtering math, injury formula, dummy factor / limit DB는 검증 장치 없이 먼저 건드리지 않는다.

## Current refactor objective
현재 문제는 계산식 자체보다 아래 경계가 뒤섞인 것이다.

- `app/ui/pages/injury_page.py`: 계산 입력 준비, 채널 선택, 상태 저장, plot, report payload 조립이 UI page에 집중됨
- `app/services/preprocessing/service.py`: filtering, derived channel, HIC, 3ms, VC helper가 한 파일에 섞임
- `app/ui/viewer_module.py`: loader UI, table, graph, cursor, preview filtering이 한 클래스에 집중됨
- `app/shell.py`: shell composition, metadata, persistence, shared dummy config, history가 한 파일에 집중됨
- `app/ui/pages/report_summary_page.py`: report UI와 export runtime orchestration 일부가 같이 있음
- report/export contract는 존재하지만 payload key 의존성이 강함
- ISO parsing은 중앙화되어 있으나 page fallback string matching과 일부 중복됨

## Phase 1 - Naming / Contract
목표:
- naming rule과 compatibility contract를 먼저 고정한다.
- 실제 rename은 최소화하고 alias를 유지한다.
- page key, class name, file name, UI label, saved metadata key를 분리해서 관리한다.

수정 후보:
- `app/shell.py`
- `app/ui/pages/dummy_set_page.py`
- `app/ui/pages/report_ploting_page.py`
- `app/report/registry.py`
- `app/report/rules/fmvss208.py`
- `app/report/templates/fmvss208_summary.py`
- `_codex/04_modules/report.md`
- `_codex/04_modules/dummy_set.md`

Subphases:
- Phase 1-A: naming 참조 검색 / contract 확인
- Phase 1-B: UI 표시명만 정리
- Phase 1-C: compatibility alias 정리 / 격리
- Phase 1-D: 실제 rename 후보 목록 작성
- Phase 1-E: 실제 rename은 별도 승인 전까지 보류

Risk:
- UI label only: LOW
- page key / class / file rename: MEDIUM to HIGH
- saved metadata key rename: HIGH

Calculation impact:
- 직접 계산 영향 없음
- 단, key mismatch가 생기면 기존 저장 결과, report, navigation이 깨질 수 있음

Validation:
- 프로그램 실행
- TEST SETUP 진입
- REPORT SUMMARY 진입
- PLOTTING page 진입
- 기존 pickle open
- SUMMARY REPORT Valuation
- Excel Export

Rollback:
- alias 유지 상태에서 UI label 변경만 되돌린다.
- internal key rename을 수행했다면 alias resolver를 먼저 확인하고 key를 기존 값으로 되돌린다.

### Phase 1-D rename candidate decision list
Phase 1-D is documentation only. Do not rename code, files, classes, or saved keys here.

| Candidate | Current locations | Recommended action | Risk | Reason |
|---|---|---|---|---|
| `report_ploting` page key | `app/shell.py`, docs, old change logs | Keep as registered internal key for now; accept `report_plotting` as alias only | MEDIUM | It is a live page key and could be referenced by saved UI state or older code |
| `ReportPlotingPage` class | `app/ui/pages/report_ploting_page.py`, `app/shell.py` import | Keep for now; rename only in a later explicit compatibility phase | MEDIUM | Class/file rename affects imports and packaging |
| `app/ui/pages/report_ploting_page.py` file | shell import and docs | Keep for now | MEDIUM | File rename requires import migration and alias wrapper |
| User-facing `PLOTING` text | nav/page label | Change to `PLOTTING` only | LOW | Display-only typo; already corrected without key rename |
| `dummyset` page key | `app/shell.py`, docs | Keep as compatibility alias to `test_setup` | MEDIUM | Older saved references may still request it |
| `DummySetPage` shim | `app/ui/pages/dummy_set_page.py` | Keep | LOW to MEDIUM | Import compatibility for older references |
| `dummy_set_page.py` file | docs/import shim | Keep as shim | LOW to MEDIUM | Removing file can break old imports |
| `shared_dummy_config` metadata key | `shell.py`, report/filtering/test setup/injury | Do not rename | HIGH | Existing pickle compatibility and multi-module data flow |
| `injury_saved_results` metadata key | `injury_page.py`, `report/engine.py` | Do not rename | HIGH | REPORT reads this key for all summary values |
| `report_saved_results.summary_report` key | `report_summary_page.py`, docs | Do not rename | HIGH | Saved REPORT reload depends on it |
| `fmvss208` rule key | `app/report/rules/fmvss208.py`, generated mapping keys | Keep stable | HIGH | Report/excel mapping uses this machine key |
| `FMVSS 208` rule label | report choices/template rules | Keep stable | MEDIUM | User-facing and template rule lookup label |
| `fmvss208_summary` template key | `app/report/templates/fmvss208_summary.py` | Keep stable | MEDIUM | Template registry lookup key |
| `head_metadata`, `*_saved_payload` slot-state keys | `injury_page.py` | Do not rename in Phase 1 | HIGH | Existing in-memory/save/restore paths and report extraction rely on these payload names |
| `result_key`, `value_key`, `payload_aliases` report item fields | `app/report/rules/*.py`, `app/report/engine.py` | Keep stable | HIGH | Core report extraction contract |
| `criterion_key` vs `dummy_profile` | injury/report payloads | Keep both; document as compatibility pair | HIGH | Limit lookup and display fallback depend on both |

Phase 1-D conclusion:
- Only user-facing typos may be corrected in Phase 1.
- Internal key/class/file renames are deferred.
- Metadata and payload keys are compatibility contracts and must not be renamed without a migration adapter.
- Old change logs may mention obsolete paths such as `app/report/regulations/fmvss208.py`; do not edit historical logs for code cleanup.

### Phase 1-E rename deferral decision
Phase 1-E is the explicit decision point for actual rename work.

Decision for `코드최적화p1`:
- Do not perform actual internal key/class/file renames in this branch.
- Keep compatibility aliases in place.
- Treat Phase 1 as complete after user review/test of the documentation and current alias behavior.
- Move any real rename into a later, separately approved compatibility phase.

Deferred rename candidates:
- `report_ploting` -> `report_plotting`
- `ReportPlotingPage` -> `ReportPlottingPage`
- `app/ui/pages/report_ploting_page.py` -> `app/ui/pages/report_plotting_page.py`
- possible future cleanup of `dummyset` and `DummySetPage` after saved-file/import compatibility is confirmed

Required conditions before any future actual rename:
1. Add alias wrapper first.
2. Keep old imports/page keys working.
3. Verify existing pickle open.
4. Verify REPORT nav/page registration.
5. Verify packaging/import paths.
6. Update `_codex/05_reference/file_to_responsibility_map.md`.
7. Get explicit user approval for the rename phase.

## Phase 2 - Low-risk split
목표:
- 계산과 무관한 UI / export runtime / style helper부터 분리한다.
- page code를 줄이되, 계산 입력과 report extraction contract는 건드리지 않는다.

수정 후보:
- `app/ui/styles.py` or `app/ui/constants.py`
- `app/report/exporters/runtime.py`
- `app/ui/pages/report_summary_page.py`
- `app/ui/pages/offset_page.py`
- `app/ui/pages/trimming_page.py`
- `app/ui/pages/report_ploting_page.py`

작업 후보:
- UI font / color / title constants 분리
- Excel export filename / execution folder / OS open helper 분리
- offset/trimming plot refresh 공통화 전 사전 분석

Risk:
- LOW
- plot refresh 공통화는 LOW to MEDIUM

Calculation impact:
- 없음

Validation:
- 모든 page 진입
- Excel export 파일명 / 저장 위치 / 자동 열기 확인
- offset/trimming preview plot 확인

Rollback:
- 이동한 helper를 page local method로 되돌린다.
- style constants 적용은 import 제거 후 literal 복원 가능해야 한다.

### Phase 2 closure decision for `코드최적화p1`
Phase 2 is limited to low-risk UI/presentation/runtime helper cleanup.

Completed scope:
- Shared Tk color/font constants in `app/ui/styles.py`.
- REPORT PLOTTING and shell style constant adoption.
- REPORT SUMMARY presentation constants in `app/ui/pages/report_summary_constants.py`.
- REPORT SUMMARY local helper wrappers for dialogs, loaded-count display, input variable handling,
  Valuation status selection, and Excel export success UI follow-up.

Explicitly deferred from Phase 2:
- `report_summary_page.py` `_build_report_payload()`
- `report_summary_page.py` `_cache_report_state_in_memory()`
- `report_summary_page.py` `_snapshot_from_saved_report()`
- `report_summary_page.py` `_report_fields()` occupant slot merge behavior
- Excel writer internals and template mapping rules
- report snapshot extraction contract
- filtering / trimming / injury calculations

Phase 2 exit condition:
1. Final whole-program user test passes.
2. Phase 2 tracker is marked closed.
3. The branch is committed and merged/pushed as requested.
4. Phase 3 starts from a new branch, not directly inside the Phase 2 branch.

## Phase 3 - Helper commonization
목표:
- 중복 helper를 공통화하되 결과 동일성 검증을 먼저 둔다.

수정 후보:
- `app/services/injury/common_engines.py`
- `app/services/injury/head_injury.py`
- `app/services/injury/chest_injury.py`
- `app/services/injury/pelvis_injury.py`
- `app/services/injury/femur_injury.py`
- `app/services/injury/tibia_injury.py`
- `app/services/injury/iliac_injury.py`
- `app/report/exporters/excel.py`
- `app/ui/pages/report_summary_page.py`

중복 정리 우선순위:
1. occupant slot merge / label 추출 helper
2. time/value valid mask
3. peak helper
4. force/moment unit conversion
5. `_gradient_contiguous`

Risk:
- occupant helper: LOW to MEDIUM
- peak/unit helper: MEDIUM
- `_gradient_contiguous`: HIGH, VC 결과 영향 가능

Calculation impact:
- peak, unit, gradient helper는 계산 결과 영향 가능성이 있으므로 snapshot 비교 필요

Validation:
- 각 injury bundle numeric metadata 비교
- report snapshot row/value/limit/status 비교
- Excel occupant label 비교
- VC 관련 값 비교

### Phase 3-A snapshot gate
Phase 3-A must be completed before any helper code move.

Required comparison targets:
- report snapshot from `app/report/engine.py` `build_report_snapshot(metadata, regulation_name)`
- saved REPORT SUMMARY payload under `report_saved_results.summary_report`
- Excel export values only when the refactor touches export mapping or occupant label resolution

Fields that must remain identical for a no-behavior-change helper refactor:
- snapshot `regulation_name`
- slot count/order and slot `slot`, `dummy_name`, `dummy_profile`
- row count/order
- row `slot`, `slot_label`, `dummy_name`, `dummy_profile`
- row `section_key`, `region`, `result_key`, `label`
- row `value`, `unit`, `limit`, `status`, `comparison`
- row `result_uid`, `value_source`, `value_path`, `limit_source`
- saved `report_fields`, including `occupant_slots`
- saved `rows`, `slots`, and `excel_mapping`

First safe candidate:
- occupant slot merge / label extraction helper.
- Keep `report_summary_page.py` wrapper methods during the first move.
- Compare `_report_fields()` output before and after.

### Phase 3-B occupant helper analysis
Phase 3-B is analysis-only.

Current locations:
- `app/ui/pages/report_summary_page.py`
  - config-to-slot extraction and merge for `report_fields.occupant_slots`
- `app/report/exporters/excel.py`
  - occupant label formatting and fallback slot merge for Excel C9/G9 export
- `app/report/engine.py`
  - snapshot slot identity from saved injury payload and shared dummy config

First implementation boundary:
- Add `app/report/occupants.py`.
- Move only pure helpers:
  - `normalize_slot_key()`
  - `occupant_slots_from_config()`
  - `merge_occupant_slots()`
- Keep `report_summary_page.py` wrapper methods during the first move.
- Do not move `_report_fields()` yet.
- Do not alter Excel exporter occupant fallback logic yet.
- Do not move report engine slot identity logic yet.

Why this boundary:
- REPORT SUMMARY currently decides the precedence of current config, metadata config,
  saved occupant slots, snapshot slots, and saved summary slots.
- Excel export has similar but not identical fallback behavior, including row-based
  extraction and `slot_label` parsing.
- Combining both at once would make C9/G9 label regressions harder to isolate.

First implementation verification:
- `_report_fields()` output must match exactly before and after.
- `report_fields.occupant_slots` order and values must match.
- Excel first and second occupant labels must remain unchanged.
- Save and `_R` reload must preserve input fields and occupant slots.

Phase 3-C implementation record:
- `app/report/occupants.py` was added with only the pure helper functions listed above.
- `report_summary_page.py` wrapper methods remain for rollback.
- `_report_fields()`, Excel exporter occupant logic, and report engine slot identity logic remain in place.

Phase 3-D implementation record:
- `app/report/occupants.py` now also owns shared occupant label helpers:
  - `occupant_label()`
  - `dummy_name_from_slot_label()`
- Excel exporter wrapper names remain stable and delegate to the shared helpers.
- `_occupant_slot_infos()` remains local to the Excel exporter.
- C9/G9 input cell detection remains unchanged.

Phase 3-E implementation record:
- `_occupant_slot_infos()` remains local to the Excel exporter but now uses
  `merge_occupant_slots()` for the final merge.
- Excel occupant precedence remains report fields, snapshot slots, then snapshot rows.
- Excel C9/G9 input cell detection remains unchanged.

Phase 3-F implementation record:
- `occupant_slot_infos_from_snapshot()` was added to `app/report/occupants.py`.
- Excel `_occupant_slot_infos()` remains as a wrapper for rollback and delegates to the shared helper.
- Excel C9/G9 input cell detection remains unchanged.

Phase 3-G/H implementation record:
- `report_fields_from_sources()` was added to `app/report/occupants.py`.
- `ReportSummaryPage._report_fields()` remains as the UI page entry point and delegates report input
  field / occupant slot assembly to the helper.
- REPORT SUMMARY occupant precedence remains current config, metadata config, saved report fields,
  current snapshot slots, then saved summary slots.
- Excel exporter unused private wrappers for slot normalization and slot-label dummy-name extraction
  were removed after their logic moved behind `occupant_slot_infos_from_snapshot()`.
- Excel `_occupant_label()` and `_occupant_slot_infos()` wrappers remain because the export flow still
  calls them directly.

Phase 3-I implementation record:
- Removed the now-unused `ReportSummaryPage._occupant_slots_from_config()` and
  `ReportSummaryPage._merge_occupant_slots()` wrappers.
- Kept `ReportSummaryPage._report_fields()` as the compatibility boundary for the page.
- Occupant helper commonization remains limited to report metadata/display assembly and does not touch
  report engine slot identity.

Phase 3-J closure decision:
- Phase 3 is closed at the occupant helper boundary.
- This branch does not continue into time/value valid mask, peak helper, force/moment unit conversion,
  or `_gradient_contiguous` commonization because those helpers are calculation-adjacent and require
  stronger numeric regression fixtures.
- Phase 4 may start only after explicit user approval and should begin with orchestration splitting,
  not filtering math or injury formula changes.
- Keep `ReportSummaryPage._report_fields()` as a page-state boundary until Phase 4 report orchestration
  work starts.

Early Phase 3 must not touch:
- peak helpers
- force/moment unit conversion
- `_gradient_contiguous`
- filtering math
- derived channel generation
- injury input resolver behavior

Rollback:
- module-local helper를 남긴 상태에서 한 module씩 import 교체한다.
- 문제가 생기면 해당 module import만 원복한다.

## Phase 4 - Orchestration split
목표:
- UI page 안에 있는 계산 준비, AUTO SET matching, metadata persistence, report orchestration을 service/helper로 분리한다.

수정 후보:
- `app/ui/pages/injury_page.py`
- `app/ui/pages/filtering_page.py`
- `app/shell.py`
- `app/ui/pages/report_summary_page.py`
- `app/services/injury/input_resolver.py`
- `app/services/filtering/presets.py`
- `app/services/state/persistence.py`
- `app/report/service.py`

이동 후보:
- `injury_page.py` `_resolve_standard_series_for_calc()`
- `injury_page.py` `_find_derived_channel()`
- `injury_page.py` `_collect_chest_disp_prefiltered()`
- `filtering_page.py` `_build_auto_filter_map()`
- `shell.py` metadata persistence assembly
- `report_summary_page.py` `_report_fields()` and occupant slot merge

Risk:
- HIGH

Calculation impact:
- injury input resolver 이동은 계산 결과 영향 가능성 HIGH
- AUTO SET matching 이동은 filtering preset 대상 영향 가능성 MEDIUM to HIGH
- persistence 이동은 existing pickle compatibility 영향 가능성 HIGH

Validation:
- selected channel, resolved source, filter label, raw source channel 비교
- AUTO SET channel_to_filter map 비교
- derived channel metadata 비교
- saved pickle metadata diff
- report snapshot diff

Rollback:
- 기존 page method를 wrapper로 남기고 새 service를 호출한다.
- 문제가 있으면 wrapper 내부를 기존 로직으로 되돌린다.
- 한 번에 한 function family만 이동한다.

### Phase 4-A/B/C implementation record
- Branch: `코드최적화p4`
- Phase 4-A moved REPORT SUMMARY payload/cache assembly helpers into `app/report/service.py`.
  `report_summary_page.py` still owns UI state and calls the report service.
- Phase 4-B moved DATA FILTERING AUTO SET preset matching into `app/services/filtering/presets.py`.
  The page still owns pending dataframe state and still calls the existing filtering engine.
- Phase 4-C moved repeated shell save metadata assembly into `app/services/state/persistence.py`.
  `shell.py` still owns save paths, pickle writing, ISO enrichment, and loaded dataset state.
- Phase 4-D moved injury derived-channel lookup into `app/services/injury/input_resolver.py`.
  `_resolve_standard_series_for_calc()` remains in `injury_page.py` because it is calculation-input
  critical and includes raw reference alignment and on-demand filtering.
- Phase 4-D follow-up fixed pandas `Index` handling in the input resolver helper.
- Phase 4-E routed REPORT SUMMARY Excel export calls through `app/report/service.py` while keeping
  UI exception handling and success follow-up in `report_summary_page.py`.
- Phase 4-F moved DATA FILTERING apply-map normalization and status-message summary helpers into
  `app/services/filtering/application.py`. The page still owns pending dataframe mutation and still
  calls `apply_filtering_with_derivatives()`.
- Phase 4-G moved DATA FILTERING commit rename helpers and filtering history summary text into
  `app/services/filtering/application.py`. `save_filters()` still owns the commit operation and
  `workbench.apply_processed_dataframe()` call.
- Phase 4-H moved DATA FILTERING commit metadata/history payload assembly into
  `build_filter_commit_payload()`. `save_filters()` still owns validation, `_F` commit, refresh, and
  user completion dialog.
- Phase 4 stops before moving `save_filters()` itself, `_resolve_standard_series_for_calc()`,
  `_collect_chest_disp_prefiltered()`, or shell state lifecycle. Those are high-risk and need
  stronger regression fixtures before Phase 5.
- Phase 4-I closure:
  - Phase 4 is closed after user testing of report, filtering, persistence, injury lookup, and
    OFFSET preview behavior.
  - High-risk moves are intentionally deferred to Phase 5 after regression fixtures are available.
  - Phase 5 must start with fixture/snapshot creation, not direct engine movement.
- These changes intentionally do not touch filtering math, derived channel generation, injury
  formulas, report extraction keys, saved metadata keys, or pickle format names.

## Phase 5 - High-risk structural split
목표:
- `app/services/preprocessing/service.py`와 dummy / ISO / rule DB를 장기 유지보수 가능한 구조로 분해한다.
- 직접 분해 전에 regression snapshot 기준선을 먼저 만든다.

수정 후보:
- `app/services/preprocessing/service.py`
- `app/services/preprocessing/filtering.py`
- `app/services/preprocessing/derived_channels.py`
- `app/services/injury/hic_engine.py`
- `app/services/injury/clip3_engine.py`
- `app/services/injury/vc_engine.py`
- `app/core/dummy/engine.py`
- `app/core/dummy/profiles/*.py`
- `app/core/isocode/engine.py`

분리 후보:
- CFC filtering engine
- derived channel builder
- HIC helper
- 3ms helper
- VC helper
- dummy factor DB schema / profile source
- ISO fallback matching

Risk:
- HIGH

Calculation impact:
- 매우 높음

Validation:
- filtering output numeric diff
- derived channel list / metadata diff
- HIC15 / HIC36 / 3ms / VC 결과 diff
- dummy factor lookup diff
- ISO parsed map diff
- existing pickle load/save diff
- `tools/capture_regression_snapshot.py` capture/compare 결과 diff

Rollback:
- 기존 `preprocessing/service.py`를 compatibility facade로 유지한다.
- public function name은 유지한다.
- 내부 import만 새 모듈로 돌린다.
- 파일 전체 이동 금지, function group 단위로 이동한다.

### Phase 5-A regression fixture gate
Phase 5-A starts with fixture tooling, not code movement.

Tool:
- `tools/capture_regression_snapshot.py`

Workflow:
- `_codex/03_workflows/regression_snapshot_workflow.md`

Required baseline before high-risk moves:
- representative saved `.pkl` after load only
- `_O`
- `_O_F`
- injury-calculated `_O_F_I` or equivalent
- REPORT SUMMARY saved `_R`

If representative files are not available, Phase 5 can only prepare the tooling and documents.
Actual preprocessing/injury input moves remain blocked until at least one baseline snapshot is
created and compared.

### Phase 5-B preprocessing classification and compare loop
Phase 5-B is still not a runtime refactor.

Allowed work:
- classify `app/services/preprocessing/service.py` function groups
- document extraction order and risk
- add folder-level snapshot capture/compare commands

Reference:
- `_codex/04_modules/preprocessing.md`
- `_codex/03_workflows/regression_snapshot_workflow.md`

Exit condition:
- `capture-dir` works on representative input files
- `compare-dir` can compare matching snapshot sets
- no app runtime calculation path is changed
- first Phase 5-C extraction candidate is selected explicitly

Phase 5-B status:
- Completed after folder-level capture/compare was verified against 5 representative H3_5%F
  two-dummy saved files.
- First Phase 5-C candidate is pure channel-role detector helpers. Do not move
  `apply_filtering_with_derivatives()` in the first Phase 5-C slice.

### Phase 5-C channel role detector extraction
First implemented extraction candidate:
- `app/services/preprocessing/channel_roles.py`

Moved only pure string helpers:
- channel role detectors
- required CFC lookup for derived role
- derived-channel name helpers

Compatibility:
- `app/services/preprocessing/service.py` keeps the same imported helper names available.

Validation:
- Phase 5 `compare-dir` must match all representative snapshots before user runtime test.

## Do not touch first
아래 영역은 검증 장치 없이 먼저 수정하지 않는다.

- filtering math
- `app/services/preprocessing/service.py` `apply_filtering_with_derivatives()`
- `app/ui/pages/injury_page.py` `_resolve_standard_series_for_calc()`
- dummy factor / IARV / limit DB
- report metric extraction key contract
- ISO rewrite / filter code rewrite
- `_gradient_contiguous`

## Quick wins allowed before high-risk work
- UI label/style constants
- report export runtime helper
- plotting page user-facing label
- documentation and phase tracker
- occupant label helper, if snapshot comparison is available

## Phase exit rule
한 phase를 끝냈다고 말하려면 아래 조건을 만족해야 한다.

1. phase tracker status가 updated 되어야 한다.
2. 변경 범위가 해당 phase 안에 있어야 한다.
3. syntax/import check가 통과해야 한다.
4. 사용자가 프로그램 테스트 결과를 알려야 한다.
5. 사용자가 다음 phase 진입을 명시적으로 승인해야 한다.
