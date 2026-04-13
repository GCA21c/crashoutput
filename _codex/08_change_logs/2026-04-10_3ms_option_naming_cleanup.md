# 2026-04-10 3ms Option Naming Cleanup

## Changed Files
- `app/ui/pages/injury_page.py`
- `app/services/injury/common_engines.py`
- `app/services/injury/head_injury.py`
- `app/services/injury/chest_injury.py`
- `app/services/injury/pelvis_injury.py`
- `app/services/preprocessing/service.py`
- `_codex/04_modules/injury_engines.md`
- `_codex/08_change_logs/2026-04-10_3ms_time_option.md`

## Reason
- `High-Res 3ms Sliding Window`는 실제 기능인 cumulative `Multiple Peak 3ms_Clip` 탐색 해상도 옵션을 정확히 설명하지 못했다.

## Behavior Impact
- UI 라벨을 `High-Resolution 3ms Search`로 통일했다.
- 개발자 코드 네이밍을 `use_high_res_cumulative_3ms` 기준으로 정리했다.
- 새 저장 키는 `use_high_res_cumulative_3ms`를 사용한다.
- 기존 저장값의 `high_res_3ms_sliding_window` 키는 읽기 호환만 유지한다.
- 계산 로직, 알고리즘, 결과값은 변경하지 않았다.

## Known Risks
- 과거 payload에 오래된 키만 들어 있는 경우는 호환 복원 경로에 의존한다.

## Follow-up
- 저장/복원된 HEAD, CHEST, PELVIS 결과를 다시 열었을 때 옵션 상태가 유지되는지 확인한다.
