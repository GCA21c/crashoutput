# 2026-04-10 3ms Time Option

## Changed Files
- `app/ui/pages/injury_page.py`
- `app/services/injury/common_engines.py`
- `app/services/injury/head_injury.py`
- `app/services/injury/chest_injury.py`
- `app/services/injury/pelvis_injury.py`
- `app/services/preprocessing/service.py`

## Reason
- `Multiple Peak 3ms_Clip`는 레퍼런스 프로그램과 맞출 때 정수/샘플-span 기반 결과가 더 가까운 경우가 있었지만, 기존 계산 방식도 유지할 필요가 생겼다.

## Behavior Impact
- HEAD, CHEST, PELVIS 패널의 `전체 계산` 왼쪽에 `High-Resolution 3ms Search` 체크박스를 추가했다.
- 기본값은 체크 상태이며, 이때는 옵션 추가 전의 기존 `Multiple Peak 3ms_Clip` 계산을 사용한다.
- 체크를 해제하면 compatibility-oriented integer/sample-span `Multiple Peak 3ms_Clip` 계산을 사용한다.
- `One Peak 3ms_Clip`과 `HIC15/HIC36` 계산은 이 옵션의 영향을 받지 않는다.
- 저장/복원된 injury payload에도 선택한 옵션 상태가 함께 보존된다.

## Known Risks
- 이 옵션은 VC용 fixed 3ms sliding mean window가 아니라 `Multiple Peak 3ms_Clip` cumulative 탐색 해상도 전환이라는 점을 문서와 코드에서 함께 유지해야 한다.

## Follow-up
- 테스트 PC에서 HEAD/CHEST/PELVIS 각각 체크 on/off 결과가 의도대로 바뀌는지 확인한다.
