# 2026-04-10 Derived CFC Raw Alignment Fix

## Changed Files
- `app/shell.py`
- `app/ui/pages/offset_page.py`
- `app/ui/pages/filtering_page.py`
- `app/ui/pages/injury_page.py`
- `app/services/preprocessing/service.py`

## Reason
- 현재 워크플로우가 `Offset -> Filtering -> Trimming`인데, filtering page가 파생 CFC 채널 재구축 기준으로 최초 로드 원본 `original_df`를 넘기고 있었다.
- 이 때문에 offset 이후 filtering을 해도 파생 채널은 offset이 반영되지 않은 최초 원본을 다시 필터링할 수 있었고, 길이 불일치 시에는 현재 채널 폴백으로 계산 경로 추적도 불명확했다.

## Behavior Impact
- workbench는 `Offset -> Filtering -> Trimming` 흐름에서 사용할 기준 raw를 `pre_filter_reference_df`로 별도 보관하고 pickle metadata에도 함께 저장한다.
- `DATA OFFSET` 확정 시 이 기준 raw가 offset 적용 결과로 갱신된다.
- filtering page는 파생 CFC 채널 재구축 기준으로 최초 로드 원본이 아니라, offset 반영 후 filtering 전 기준 데이터(`pre_filter_reference_df`)를 넘긴다.
- 파생 CFC 채널 생성은 기존 헬퍼 `_resolve_filter_source_series()`를 사용해 현재 시간축에 맞춘 기준 소스를 우선 해석한다.
- raw-aligned 재구축 여부가 `filter_history.source_mode`와 `created_from_raw` 메타데이터에 실제 계산 경로대로 기록된다.
- injury page의 목표 CFC 보정 경로도 `pre_filter_reference_df`를 사용하므로, head/neck/chest/femur 계산에서 누락된 CFC를 즉석 재구축할 때 offset 이전 원본이 아니라 offset 이후 기준 raw를 참조한다.
- 기준 소스 정렬이 정말 불가능한 경우에만 현재 채널 값으로 폴백한다.

## Known Risks
- 원본 time 축 품질이 낮거나 중복/비정상 값이 많으면 raw-aligned 보간 결과가 NaN 위주가 될 수 있고, 그때는 기존처럼 현재 채널 폴백이 발생한다.
- pickle metadata 안에 기준 raw dataframe이 추가로 저장되므로 파일 크기는 이전보다 커질 수 있다.

## Follow-up
- offset 후 filtering preview에서 chest displacement 파생 CFC600 채널이 offset 반영값을 기준으로 생성되는지 확인이 필요하다.
- filtering 또는 trimming 후 저장한 pickle을 다시 열었을 때도 injury 계산의 raw 재구축 기준이 동일하게 유지되는지 회귀 확인이 필요하다.
