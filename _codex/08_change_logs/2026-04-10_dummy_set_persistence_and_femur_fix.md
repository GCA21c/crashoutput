# 2026-04-10 Dummy Set Persistence And Femur Fix

## Changed Files
- `app/shell.py`
- `app/ui/pages/injury_page.py`

## Reason
- `_I.pkl` 저장 시 injury 결과/그래프 메타는 저장되지만 `DUMMY SET` 공통 설정이 metadata에 포함되지 않아, 저장된 결과 파일을 다시 열었을 때 더미 배치/프로필 상태가 바로 복원되지 않았다.
- `FEMUR 전체 계산` 버튼은 존재하지 않는 `calculate_femur` 메서드를 호출하고 있어 Tkinter callback 오류가 발생했다.

## Behavior Impact
- `shared_dummy_config`가 `_I.pkl` 저장 metadata에 포함된다.
- 저장된 pickle 로드 시 `shared_dummy_config`를 다시 workbench와 injury pages에 적용한다.
- `DUMMY SET`에서 `SET!`를 누르면 현재 pickle이 열려 있는 경우 metadata에도 즉시 반영된다.
- `FEMUR 전체 계산` 버튼은 실제 `calculate_femur` 메서드를 호출하며, 기존 legacy 진입점도 동일 동작으로 유지된다.

## Known Risks
- 기존에 저장된 `_I.pkl`에는 `shared_dummy_config`가 없으므로, 그 파일들은 새 저장 전까지는 예전처럼 기본 더미 설정으로 열린다.

## Follow-up
- 필요하면 `DUMMY SET` 변경 자체를 별도 history entry로 남겨 추적성을 더 강화할 수 있다.
