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
| Phase 1-D | Ready for user review | rename candidate list documented; no code rename |
| Phase 1-E | Not started | actual rename deferred |
| Phase 2 | Blocked | Do not start until Phase 1 is explicitly closed by user |
| Phase 3 | Blocked | Requires snapshot comparison criteria |
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
User review for Phase 1-D rename candidate decisions.

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

## Hard block
Do not proceed to Phase 2 yet.
