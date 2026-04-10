# 2026-04-10 Derived CFC Raw Alignment Fix

## Changed Files
- `app/services/preprocessing/service.py`

## Reason
- 파생 CFC 채널 생성 로직이 `original_df`와 현재 작업 데이터 길이가 다를 때 raw-aligned 재구축 대신 현재 채널 값으로 조용히 폴백했다.
- 이 경우 트리밍/오프셋 이후 선택 채널이 이미 필터된 상태면 파생 채널이 다시 필터링될 수 있어, 저장소 원칙인 raw -> filter 추적성과 double-filter 방지 규칙에 어긋났다.

## Behavior Impact
- 파생 CFC 채널 생성은 기존 헬퍼 `_resolve_filter_source_series()`를 사용해 현재 시간축에 맞춘 원본(raw) 값을 우선 해석한다.
- raw-aligned 재구축 여부가 `filter_history.source_mode`와 `created_from_raw` 메타데이터에 실제 계산 경로대로 기록된다.
- 원본 정렬이 정말 불가능한 경우에만 현재 채널 값으로 폴백한다.

## Known Risks
- 원본 time 축 품질이 낮거나 중복/비정상 값이 많으면 raw-aligned 보간 결과가 NaN 위주가 될 수 있고, 그때는 기존처럼 현재 채널 폴백이 발생한다.

## Follow-up
- trimming/offset 이후 filtering preview에서 chest displacement 파생 CFC600 채널이 raw-aligned로 유지되는지 샘플 데이터로 회귀 확인이 필요하다.
