# 2026-04-14 REPORT summary saved rows restore

- 무엇을: `SUMMARY REPORT` 저장 payload에 화면 복원용 row 메타를 함께 넣고, 저장된 `rows`/`slots`를 다시 열 때 즉시 트리에 복구하도록 보완했다.
- 왜: 기존에는 `report_fields`만 로드하고 `on_show()`에서 waiting 상태로 초기화해서, 저장된 결과 리스트가 파일에 있어도 화면에 복원되지 않았다.
- 어디를: `app/ui/pages/report_summary_page.py`
- 리스크: 구버전 저장 파일은 row 메타가 부족할 수 있으나, regulation definition과 slot 정보로 가능한 범위까지 복원하도록 fallback 처리했다.
