# Report plotting module

## Main code paths
- `app/ui/pages/report_ploting_page.py`
- `app/report/plotting_service.py`
- `app/report/plotting_config.py`
- `app/report/exporters/ppt.py`
- `app/report/exporters/runtime.py`

## Current role
- collect graph items from injury modules
- show graph load state and text preview
- save plotting item selection/order/text mode into report metadata cache
- export plotting report into PPT template under `resources/templates/`

## Current data source
- plotting canonical source is `injury_saved_results`
- plotting item context may contain:
  - `canonical_metrics`
  - `canonical_graphs`
  - `calculation_context`
  - `report_values`
  - `metric_extrema`
  - `structured_metrics`
  - `summary_text`

Preferred read order:
1. canonical payload layers
2. compatibility/cache layers

## Graph text policy
- graph text is formatter-owned output, not canonical stored text
- payload stores data; formatter rules in `plotting_service.py` and `plotting_config.py` decide:
  - labels
  - indentation
  - multiline layout
  - injury block placement
- trailing blank line from pasted examples should be ignored at final formatter output

## Template policy
- PPT template path:
  - `resources/templates/testid_Plot.pptx`
- 템플릿 text box marker를 찾아 내용을 치환한다
- 폰트, 위치, 스타일은 템플릿 기준을 우선한다
- 텍스트 박스 내용만 바꾸고 템플릿 스타일 자체는 코드가 새로 만들지 않는다

## Current formatter coverage
- completed:
  - `HEAD X/Y/Z`
  - `HEAD RESULTANT`
  - `NECK FO`
  - `NECK MO`
  - `NECK MOCy`
  - `NECK Nij - Components`
  - `NECK Nij - Overall`
  - `CHEST Acceleration`
  - `CHEST Displacement`
  - `CHEST V*C`
  - `PELVIS`
  - `FEMUR Combined`
  - `KNEE Combined`
  - `ILIAC Force`
  - `ILIAC Moment`
  - `ILIAC Fx-My`
- deferred:
  - `TIBIA`

## Windows note
- PPT export writer itself is `python-pptx`
- export 후 자동 open은 runtime helper가 OS file association으로 수행한다
- Windows/Office 정책 변경에 따라 PowerPoint background process가 남을 수 있다
- 이는 COM 제어보다 `open_export_file()` 자동 오픈 경로의 영향으로 보는 것이 맞다

## Next direction
- representative `.dat` 기반 자동 회귀에 plotting preview/text를 포함한다
- formatter는 canonical payload 의존도를 더 높이고 legacy fallback을 점진적으로 축소한다
