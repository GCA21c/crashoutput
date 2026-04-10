# 2026-04-10 Multiple Peak 3ms Sample Span Experiment

## Changed Files
- `app/services/preprocessing/service.py`

## Reason
- 레퍼런스 프로그램과 비교할 때 `Multiple Peak 3ms_Clip` 값이 현재 구현보다 약간 낮게 나와, 상수 샘플레이트 경로의 샘플 수 판정 규칙 차이를 실험한다.

## Behavior Impact
- cumulative Xms 상수 샘플레이트 경로에서 필요한 표본 수를 `ceil(x/dt)`가 아니라 `ceil(x/dt) + 1`로 계산한다.
- 즉 `x ms`를 만족하는 데 필요한 시간 span을 `sample intervals`가 아니라 `first sample`부터 `last sample`까지의 span으로 해석한다.

## Known Risks
- 이 변경은 레퍼런스 정렬 실험용이며, 일부 데이터에서는 기존 값보다 더 낮아질 수 있다.
- non-uniform sampling fallback 경로에는 영향이 없다.

## Follow-up
- head/chest의 `Multiple Peak 3ms_Clip` 값을 레퍼런스 프로그램과 다시 비교해 차이가 줄어드는지 확인한다.
