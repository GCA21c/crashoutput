# 2026-04-14 REPORT summary module v1

- 무엇을: `REPORT` 네비게이션과 `SUMMARY REPORT` / `PLOTING` 페이지를 추가하고, FMVSS 208 기준의 uid 결과 매핑/저장 구조를 분리했다.
- 왜: 기존 injury 계산값을 재계산하지 않고 요약 리포트로 읽어 보여주기 위해서다.
- 어디를: `app/shell.py`, `app/report/`, `app/ui/pages/report_summary_page.py`, `app/ui/pages/report_ploting_page.py`
- 리스크: neck/chest/femur 일부 값은 저장 payload에 구조화 수치가 없어 `summary_text` 파싱에 의존하며, 저장된 텍스트 형식이 바뀌면 REPORT 매핑도 함께 맞춰야 한다.
