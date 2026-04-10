# 2026-04-10 Injury Graph Tab Persistence Normalization

## Changed Files
- `app/ui/pages/injury_page.py`

## Reason
- 상해 모듈별 그래프 탭 저장 경로가 일관되지 않아, 계산 후 기본 탭으로 다시 돌아가거나 메뉴 이동 후 마지막 보던 탭이 복원되지 않는 문제가 있었다.

## Behavior Impact
- 그래프 탭 선택 시 `graph_key` / `graph_uid`를 slot state와 모듈별 saved payload에 함께 저장하도록 통일했다.
- 계산 직후에도 현재 모듈에서 마지막으로 보던 유효한 탭이 있으면 그 탭을 유지하고, 없을 때만 기본 탭을 사용한다.
- `CHEST` 그래프는 복원 시 실제 notebook 탭 selection까지 같이 적용되도록 정리했다.
- `NECK`는 `nij_components` / `nij_overall` key 구조를 기준으로 저장/복원한다.

## Known Risks
- 과거 저장값에 남아 있는 오래된 graph key alias는 모듈별 normalize 경로에 의존한다.

## Follow-up
- HEAD, NECK, CHEST, FEMUR, ILIAC, TIBIA에서 탭을 바꾼 뒤 다른 메뉴로 이동했다가 돌아와도 마지막 탭이 유지되는지 확인한다.
