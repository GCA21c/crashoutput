# REPORT-PLOTTING wide template export

## What changed
- `resources/templates/testid_Plot.pptx`의 wide 템플릿 기준 marker와 plot 영역을 export 코드가 다시 읽도록 확인했다.
- PPT export 시 graph image를 `Plot here` placeholder 크기 비율에 맞춰 렌더링한다.
- PPT 삽입 시 강제 width/height stretch 대신 placeholder 내부에 aspect-ratio 유지 방식으로 배치한다.
- PPT export 중 사용자가 프로그램 다운으로 오해하지 않도록 main window 위에 대기 overlay와 determinate progress bar를 표시한다.

## Files
- `app/report/exporters/ppt.py`
- `app/report/plotting_service.py`
- `app/ui/pages/report_ploting_page.py`

## Risk
- 로컬 macOS 환경에는 `python-pptx`가 설치되어 있지 않아 실제 PPT 저장은 Windows 실행 환경에서 확인해야 한다.
- 문법 검사와 템플릿 marker 검출은 통과했다.
