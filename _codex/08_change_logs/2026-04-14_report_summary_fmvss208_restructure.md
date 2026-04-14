# 2026-04-14 REPORT summary FMVSS208 restructure

- 무엇을: `REPORT SUMMARY`의 FMVSS 208 항목 순서와 라벨을 HEAD/NECK/CHEST/FEMUR/KNEE 순으로 재정의하고, 법규 정의를 `app/report/regulations/` 아래 파일 단위로 분리했다.
- 왜: 사용자가 지정한 FMVSS208 보고 항목 구성을 그대로 반영하고, 이후 다른 법규 기준을 같은 패턴으로 쉽게 추가할 수 있게 하기 위해서다.
- 어디를: `app/report/definitions.py`, `app/report/regulations/__init__.py`, `app/report/regulations/fmvss208.py`, `app/report/mapping.py`, `app/ui/pages/report_summary_page.py`
- 리스크: `KNEE`는 현재 더미 엔진에 `slider_displacement_limit_mm` 기준값이 없어 LIMIT가 `N/A`로 남는다. 기준값을 쓰려면 이후 `app/core/dummy/engine.py`의 `knee` 모듈 팩터를 채워야 한다.
- 메모: `Peak Extension MOCy`는 엔진 저장값이 음수 방향 peak이므로, REPORT에서는 절대값으로 읽어 LIMIT와 비교하도록 보정했다.
