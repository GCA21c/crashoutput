# Current Program State

새 세션이 현재 프로그램 상태와 다음 개발 방향을 빠르게 파악하기 위한 요약 정본이다.

## Baseline
- production branch: `main`
- product title: `Crashoutput™ Ver 1.0`
- UI workflow: Data Viewer -> Test Setup -> Offset -> Filtering -> Trimming -> Injury -> Report Summary -> Plotting -> Video Analysis
- core policy: 계산값 원본성, raw reference, ISO/dummy routing, payload/registry 일관성을 우선한다.

## Current Status
- DAT/CSV load, offset, filtering, trimming, injury calculation, report summary, plotting export의 큰 흐름은 구축 완료 상태다.
- DAT `.dig` payload 참조를 지원한다. 기존 `.dat/.chn` raw loading 원칙은 유지한다.
- Video Analysis는 구축 완료 단계다.
  - `Normal Mode`: 기존 OpenCV streaming/cache/prefetch
  - `Boost Mode`: video 전체 frame RAM preload
  - UI 확장 모드, pulse overlay, keyframe timeline, sync offset 기능이 있다.
- startup splash는 `main.py`에서 앱 shell import 전에 표시한다.

## Result Architecture
- 결과 정본은 `metadata["injury_saved_results"]`와 payload/registry 계층을 기준으로 한다.
- 주요 registry:
  - `injury_result_registry`
  - `injury_graph_registry`
  - `injury_slot_registry`
- formatter/report/plotting/export는 가능한 한 같은 payload 정본을 읽어야 한다.
- legacy/cache 필드는 호환 때문에 남아 있을 수 있으나 새 기능의 정본으로 늘리지 않는다.

## Report / Export Direction
- REPORT SUMMARY는 계산된 payload를 valuation table로 정리한다.
- REPORT PLOTTING은 graph payload와 formatter text를 PPT template 위치에 export한다.
- template 좌표, graph mapping, text formatter는 분리 가능한 구조를 유지한다.
- 향후 시험모드/평가목적별 export template과 valuation rule을 확장한다.

## Next Product Direction
- 다음 개발의 중심은 “시험모드별 dummy/injury criteria 확장”이다.
- 진행 순서:
  1. 시험모드별 사용 dummy와 적용 injury criteria 파악
  2. 법규 시험/상품성 시험/NCAP/IIHS 등 평가 목적 구분
  3. 필요한 injury 계산 엔진 추가
  4. 결과를 payload/registry에 저장
  5. SUMMARY REPORT valuation에 연결
  6. PLOTTING/PPT/Excel export template에 연결
  7. sample DAT 기반 자동 테스트 구축

## Work Rules For Future Codex
- 사용자 요청 범위 안에서만 수정한다.
- 계산식/평가기준/필터링 기준은 `crash-reference` MCP로 근거 확인 후 변경한다.
- 이미 필터링된 채널을 의도적으로 다시 필터링하지 않는다.
- 신규 injury는 `section + slot + graph_key/result_uid/graph_uid` 추적 가능성을 유지한다.
- 사용자 승인 없이 공통규칙화/일반화 범위를 넓히지 않는다.
