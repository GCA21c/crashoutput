# 2026-04-14 REPORT summary UI layout refresh

- 무엇을: `REPORT - SUMMARY` / `REPORT - PLOTING` 상단 제목을 추가/정리하고, SUMMARY 페이지의 평가모드 라벨, 입력 필드 배치, `Test DATE` 입력/표시, 정보 박스 높이를 조정했다.
- 왜: REPORT 화면의 상단 구조가 약하고 입력/정보 영역의 세로 공간을 과도하게 차지해서 사용성이 떨어졌기 때문이다.
- 어디를: `app/ui/pages/report_summary_page.py`, `app/ui/pages/report_ploting_page.py`, `app/report/excel_mapping.py`
- 리스크: 기존 저장 데이터에는 `test_date`가 없을 수 있으나, 로딩 시 빈 문자열로 처리되므로 기존 파일과의 호환은 유지된다.
