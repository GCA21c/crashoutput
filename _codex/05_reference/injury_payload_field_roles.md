# Injury payload field roles

이 문서는 payload 강화 이후 남아 있는 결과 필드들을
`정본 / cache / 표현층 / 제거후보`로 나누기 위한 기준선이다.

## 정본 원칙
- persisted canonical store: `metadata["injury_saved_results"]`
- canonical 본문:
  - `canonical_metrics`
  - `canonical_graphs`
  - `calculation_context`
- registry:
  - `injury_result_registry`
  - `injury_graph_registry`
  - `injury_slot_registry`

`slot_states`는 UI/runtime cache이고 정본이 아니다.

## 필드 역할표
| Field | 현재 역할 | 분류 | 주 소비자 | 비고 |
|---|---|---|---|---|
| `canonical_metrics` | section + metric + axis/component 기준 계산 결과 본문 | 정본 | plotting formatter, summary report, 향후 export formatter | 신규 canonical 본문. 앞으로 확장 기준 |
| `canonical_graphs` | graph key가 어떤 metric series를 묶는지 설명 | 정본 | plotting formatter, graph composition, 향후 graph title/label policy | overlay graph를 값이 아니라 composition으로 표현 |
| `calculation_context` | 입력채널, criterion, dummy, flags, 주요 계산 파라미터 | 정본 | plotting formatter, summary/report, 향후 provenance 표시 | 결과 metric과 분리된 계산 컨텍스트 층 |
| `structured_metrics` | 계산 엔진이 만든 가장 풍부한 raw result dict | 정본 보조층 | canonical builder, legacy plotting/report fallback | 현재는 canonical 생성의 원재료 역할도 함 |
| `report_values` | report/export용 scalar projection | cache | summary report, plotting fallback, excel export 경유 | 당장 제거 대상 아님. canonical 전환 완료 후 축소 후보 |
| `metric_extrema` | plotting/report용 extrema cache | cache | plotting formatter, 일부 report fallback | `canonical_metrics`가 자리 잡은 뒤 축소 후보 |
| `summary_text` | 각 모듈 결과요약 UI 텍스트 | 표현 cache | injury page, plotting legacy fallback | 텍스트 자체는 정본이 아니라 presentation cache |
| top-level flatten scalar | 과거 report/plotting/reload 호환용 미러 값 | 호환 cache | legacy report/plotting/read path | 장기 삭제 후보 |
| `*_saved_payload` in `slot_states` | section별 runtime bridge cache | UI/runtime cache | injury page graph restore/rebuild | payload store 직접 소비 전환 후 축소 후보 |
| `slot_states[*].summary_text` 등 | 현재 활성 탭 UI 상태 | UI/runtime cache | injury page UI | persisted canonical store와 별개 |

## 소비자별 현재 우선 경로

### graph rendering
- owner: `app/ui/pages/injury_page.py`
- 현재 경로:
  1. `slot_states`
  2. 필요 시 canonical payload store에서 hydrate
  3. graph rebuild
- 메모:
  - 아직 UI runtime cache 의존이 남아 있음
  - canonical payload만으로 직접 그리는 단계는 아님

### plotting
- owner: `app/report/plotting_service.py`
- 현재 경로:
  1. `canonical_metrics`
  2. `calculation_context`
  3. `canonical_graphs`
  4. legacy fallback: `metric_extrema`, `structured_metrics`, `report_values`, `summary_text`
- 메모:
  - `HEAD/NECK/CHEST`는 canonical direct read 범위가 가장 넓음
  - 나머지 모듈은 graph text explicit rule 범위를 단계적으로 확대 중

### summary report
- owner: `app/report/engine.py`, `app/report/rules/fmvss208.py`
- 현재 경로:
  1. rule의 `canonical_aliases`, `context_aliases`
  2. legacy fallback: `report_values`, `structured_metrics`, top-level payload
- 메모:
  - `HEAD/NECK/CHEST` canonical 전환이 가장 앞서 있음
  - `PELVIS/FEMUR/KNEE`는 일부 canonical alias가 붙어 있음

### excel export
- owner: `app/report/exporters/excel.py`
- 현재 경로:
  1. `SUMMARY REPORT snapshot`
  2. exporter template mapping
- 메모:
  - 직접 payload를 읽지 않고 summary snapshot을 경유하므로, report engine 정리가 먼저다

### reload
- owner: `app/ui/pages/injury_page.py`
- 현재 경로:
  1. `injury_saved_results`
  2. `slot_states` hydrate
  3. per-section `*_saved_payload` bridge
- 메모:
  - reload 안정화는 됐지만 bridge cache가 아직 남아 있다

## 레거시 정리 기준

### 유지
- `canonical_metrics`
- `canonical_graphs`
- `calculation_context`
- `injury_saved_results`
- registry 3종

### 당분간 cache로 유지
- `structured_metrics`
- `report_values`
- `metric_extrema`
- `summary_text`

### 장기 축소/제거 후보
- top-level flatten scalar
- section별 `*_saved_payload`
- section payload 내부 중복 registry/alias

## 다음 단계 판단 기준
1. plotting formatter가 legacy fallback 없이도 충분한가
2. summary report가 canonical/context만으로도 충분한가
3. reload가 bridge payload 없이도 안정적인가

이 세 조건이 충족되면 그때:
- `report_values` 축소
- `metric_extrema` 축소
- flatten field 제거
- `*_saved_payload` 제거
순으로 간다.
