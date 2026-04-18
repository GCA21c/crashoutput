# Refactor phase tracker

이 문서는 현재 리팩토링 진행 위치를 기록한다.
다음 작업을 시작하기 전 항상 이 문서를 확인한다.

## Current branch
- `코드최적화p1`

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
| Phase 3 | Ready on new branch | Requires snapshot comparison criteria before code changes |
| Phase 4 | Blocked | Requires Phase 1-3 completion |
| Phase 5 | Blocked | Requires regression coverage and explicit approval |

## Completed work on this branch
- Added `app/report/exporters/runtime.py`.
- Moved Excel export runtime helpers out of `app/ui/pages/report_summary_page.py`.
- Documented report naming / compatibility contract in `_codex/04_modules/report.md`.
- Documented report snapshot regression criteria in `_codex/04_modules/report.md`.
- Corrected user-facing PLOTTING labels while retaining legacy `report_ploting` identifiers.
- Added `PAGE_KEY_ALIASES` in `app/shell.py`.
- Documented `dummyset` and `DummySetPage` compatibility requirements.

## Current next action
Create Phase 3 branch and define snapshot comparison criteria before code changes.

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
