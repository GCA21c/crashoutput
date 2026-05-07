# Current Handoff

새 세션 재개용 최소 handoff다. 상세 이력은 `_codex/08_change_logs/`에 보관하되 기본으로 읽지 않는다.

## Current Baseline
- repo root: `/Users/gca_mac/Desktop/workspace/crashoutput`
- active production baseline: `main`
- app version: `Crashoutput™ Ver 1.0`
- current architecture baseline: data load -> preprocessing -> injury calculation -> payload/registry -> summary/plotting/export
- Video Analysis는 기능 구축 완료 단계이며, `Normal Mode`와 `Boost Mode` video load를 선택한다.

## Product Direction
- 전체 workflow 틀은 구축된 상태다.
- 앞으로의 핵심 작업은 시험모드별 dummy와 injury criteria를 정리하고, 필요한 상해계산을 추가하는 것이다.
- 계산 결과는 payload/registry에 저장하고, report/plotting/export가 같은 정본 데이터를 읽게 유지한다.
- 시험모드와 평가 목적에 따라 report valuation 및 template export를 확장한다.
  - 예: 법규 시험, 상품성 시험, NCAP/IIHS 등 목적별 평가/출력 구분

## v101 SIDE/FMVSS214 Caution
- `v101`의 SIDE/FMVSS214 방향은 폐기 대상으로 기록됐다.
- 실패 기록: `_codex/08_change_logs/2026-05-08_v101_fmvss214_side_failed_direction.md`
- 다음 재시작 시 기존 INJURY UI/모듈 패턴을 반드시 유지하고, 새 SIDE 모듈 구조는 사용자 확인 후 구현한다.
- 독립 통합형 `SIDE IMPACT` 페이지 방식은 재사용하지 않는다.

## Immediate Reading Order
1. `AGENTS.md`
2. `_codex/02_rules/dev_rules.md`
3. `_codex/03_workflows/current_program_state.md`
4. 요청과 직접 관련된 `_codex/04_modules/*.md`
5. 필요한 코드 파일만 최소 확인

## Do Not Do
- 프로그램 로직을 문서 정리 목적으로 건드리지 않는다.
- 과거 refactor/change log 전체를 새 세션 초기에 읽지 않는다.
- 계산식/규정/필터링 기준 변경은 `crash-reference` MCP 우선 확인 없이 진행하지 않는다.
