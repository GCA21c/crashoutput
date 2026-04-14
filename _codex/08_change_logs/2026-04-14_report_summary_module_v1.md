# 2026-04-14 REPORT summary module v1

- 무엇을: `REPORT` 네비게이션과 `SUMMARY REPORT` / `PLOTING` 페이지를 추가하고, FMVSS 208 기준의 uid 결과 매핑/저장 구조를 분리했다.
- 왜: 기존 injury 계산값을 재계산하지 않고 요약 리포트로 읽어 보여주기 위해서다.
- 어디를: `app/shell.py`, `app/report/`, `app/ui/pages/report_summary_page.py`, `app/ui/pages/report_ploting_page.py`
- 리스크: neck/chest/femur 일부 값은 저장 payload에 구조화 수치가 없어 `summary_text` 파싱에 의존하며, 저장된 텍스트 형식이 바뀌면 REPORT 매핑도 함께 맞춰야 한다.
- 후속 수정: `_R` 저장 시 존재하지 않는 원본 폴더 대신 현재 유효 폴더로 fallback 하도록 보완했고, REPORT는 `Valuation` 클릭 전까지 대기 상태로 바꿨다.
- 후속 수정 2: `REPORT`가 `summary_text`를 파싱하지 않도록 바꾸고, 각 상해 모듈 저장 payload에 `report_values`, `structured_metrics`, `metric_extrema`를 함께 저장하도록 정리했다.
- 후속 수정 3: REPORT 저장 파일명은 현재 작업 단계 파일명 뒤에 `_R`을 붙이도록 조정했고, 페이지 이동 후에도 REPORT 입력/valuation 상태를 메모리에서 유지하도록 보완했다.
- 후속 수정 4: `NECK`의 Peak Tension / Peak Compression 같은 REPORT 대상 scalar는 uid 결과 payload 최상단에도 함께 펼쳐 저장하도록 보강했다. 원인은 uid 충돌이 아니라 neck scalar 값의 직접 저장 부족이었다.
