# 2026-04-10 Neck Graph And Summary UI Update

## Changed Files
- `app/ui/pages/injury_page.py`
- `app/services/injury/neck_injury.py`

## Reason
- NECK 그래프를 force/moment overlay와 MOCy, Nij 중심으로 분리해서 보고 싶고, 결과 요약에도 upper neck force/moment 축별 max/min과 발생 시각을 함께 표시할 필요가 생겼다.

## Behavior Impact
- NECK 그래프 탭을 `NECK FO`, `NECK MO`, `MOCy`, `UPPER NECK INDEX Nij`로 구성했다.
- FO 그래프는 `Fx/Fy/Fz`, MO 그래프는 `Mx/My/Mz`를 오버레이한다.
- MOCy 그래프와 Nij 그래프를 별도 탭으로 표시한다.
- Neck summary에 `UPPER NECK FORCE` / `UPPER NECK MOMENT` 블록을 추가해 각 축의 filter label, max, min, 발생 시각을 표시한다.
- 계산 로직과 Nij 계산식은 변경하지 않았다.

## Known Risks
- summary의 축별 max/min은 선택 채널과 부호 옵션을 반영한 표시용 정보이며, Nij 계산에 쓰는 내부 CFC 선택 규칙과는 별개다.

## Follow-up
- 멀티더미 상태에서 탭 저장/복원 시 `fo/mo/mocy/nij` graph key가 안정적으로 유지되는지 확인한다.
