# Current program state

이 문서는 현재 프로그램 상태와 바로 다음 작업 방향을 빠르게 파악하기 위한 요약 정본이다.
다른 세션의 Codex는 상세 코드 탐색 전에 이 문서를 먼저 확인한다.

## Current branch baseline
- active maintained branch: `v095`
- payload 강화 1차와 REPORT-PLOTTING 초기 구축이 반영된 상태다
- 사용자 확인 기준으로 `HEAD / NECK / CHEST / PELVIS / FEMUR / KNEE / ILIAC`의 주요 흐름은 정상 동작했다
- `TIBIA`는 graph/payload 구조는 존재하지만 plotting text formatter는 후속 작업으로 남겨둔 상태다

## Program status summary

### 1. Data / preprocessing
- `.dat` load, filtering, offset, trimming, injury calculation의 핵심 계산 흐름은 현재 사용자 기준으로 안정 상태다
- DAT `215` 처리 정책은 raw sample을 보존하고 header `215` 값은 `dat_channel_novalue_map` 메타데이터로만 유지한다
- `_T` 저장은 trimming 이후 injury 결과를 끌고 가지 않도록 경계가 수정됐다

### 2. Injury result architecture
- canonical persisted result owner는 `metadata["injury_saved_results"]`
- 공통 store/registry:
  - `injury_result_registry`
  - `injury_graph_registry`
  - `injury_slot_registry`
- canonical payload layers:
  - `canonical_metrics`
  - `canonical_graphs`
  - `calculation_context`
- compatibility/cache layers는 아직 남아 있다:
  - `structured_metrics`
  - `report_values`
  - `metric_extrema`
  - `summary_text`
  - top-level flatten 값들
  - `slot_states[*]`, `*_saved_payload`

### 3. REPORT SUMMARY
- `SUMMARY REPORT`는 canonical payload alias를 먼저 읽고 legacy field로 fallback 한다
- `HEAD / NECK / CHEST`는 canonical read 전환이 가장 많이 진행된 상태다
- `PELVIS / FEMUR / KNEE`도 일부 canonical alias가 반영됐다
- `_R` 저장/재로드는 정상 확인됐다

### 4. REPORT - PLOTTING
- page key는 legacy compatibility를 위해 여전히 `report_ploting`이다
- UI:
  - `Load Plot`
  - `Save`
  - `PPT EXPORT`
- report inputs는 REPORT SUMMARY 입력값을 공통 참조한다
- plotting item은 canonical payload를 우선 읽고 legacy field로 fallback 한다
- PPT export는 `python-pptx` 기반으로 템플릿 marker text box를 찾아 내용을 치환하는 방식이다
- Windows에서 export 후 PPT를 자동으로 열면 Office background process가 남을 수 있다
  - 직접 원인은 COM 제어가 아니라 `os.startfile()` 자동 오픈 경로다

### 5. Graph text formatter status
- formatter는 그래프별 explicit rule + canonical payload accessor 구조로 옮겨간 상태다
- 정리 완료 범위:
  - `HEAD X/Y/Z`
  - `HEAD RESULTANT`
  - `NECK FO`
  - `NECK MO`
  - `NECK MOCy`
  - `NECK Nij - Components`
  - `NECK Nij - Overall`
  - `CHEST Acceleration`
  - `CHEST Displacement`
  - `CHEST V*C`
  - `PELVIS`
  - `FEMUR Combined`
  - `KNEE Combined`
  - `ILIAC Force / Moment / Crossplot`
- 후속 남은 범위:
  - `TIBIA` plotting text
  - formatter fallback 축소

## Current architectural direction

### payload direction
- 내부 기준은 `section + metric + axis/component` 구조를 지향한다
- `Head_Resultant` 같은 부위명 결합 key보다
  - `section=head`
  - `metric=resultant`
  구조를 우선한다
- overlay graph는 하나의 값이 아니라 `canonical_graphs`에서 metric composition으로 표현한다

### formatter direction
- 데이터는 payload 정본에서 읽고
- 사람에게 보이는 label, multiline layout, graph text는 formatter가 만든다
- graph title, plotting label, ppt text는 payload 정본이 아니라 formatter/policy layer가 책임진다

## Immediate next direction
- 다음 우선순위는 `샘플데이터 수집 및 DAT 기반 테스트 자동화 구축`
- 목표:
  1. 대표 `.dat` 샘플 세트 정리
  2. 각 샘플의 검증 목적 문서화
  3. data load -> preprocessing -> injury calculation -> payload -> summary report -> plotting text 자동 회귀 실행
  4. 마지막 PPT export만 수동 확인

## Deferred improvement notes
- REPORT-PLOTTING background export:
  - 현재 export는 UI page의 matplotlib figure/canvas를 재사용하므로 완전한 worker thread 분리가 아직 안전하지 않다
  - 장기적으로 graph rendering을 headless matplotlib renderer로 분리한 뒤 PPT 조립/저장을 worker thread로 내려 창 이동/최소화 끊김을 줄인다
  - 이 작업은 pilot graph부터 시작해 기존 화면 그래프와 export 그래프 스타일이 달라지지 않는지 검증해야 한다

## What future Codex should do first
1. `AGENTS.md`
2. `_codex/02_rules/dev_rules.md`
3. 이 문서
4. `_codex/05_reference/injury_payload_field_roles.md`
5. 요청 범위에 맞는 `_codex/04_modules/*.md`

## Do not forget
- 계산식 변경보다 저장/조회/formatter 구조 정리가 현재 우선순위다
- legacy key는 아직 compatibility contract라서 바로 지우지 않는다
- 사용자가 명시적으로 승인하기 전 공통규칙화/일반화 범위를 먼저 넓히지 않는다
