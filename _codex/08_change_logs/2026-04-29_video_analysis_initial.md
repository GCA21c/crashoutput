# Video Analysis initial build

## What changed
- `POST-PROCESSING > ANALYSIS > VIDEO ANALYSIS` 신규 메뉴와 페이지를 추가했다.
- OpenCV 기반 video load, 최대 2개 video slot, frame step/play/pause, sync frame offset 표시를 구현했다.
- 기존 viewer dataset channel을 최대 3개까지 pulse graph에 추가하고 video frame cursor와 연동한다.
- Key frame timeline은 duration bar/current marker/keyframe placeholder로 초기 구축했다.

## Files
- `app/shell.py`
- `app/ui/pages/video_analysis_page.py`
- `app/ui/components/video_viewer.py`
- `app/ui/components/pulse_timeline.py`
- `app/core/video/video_sync.py`
- `_codex/04_modules/video_analysis.md`

## Risk
- 로컬 macOS Python에는 `_tkinter`가 없어 실제 UI 실행은 Windows/Tk 환경에서 확인해야 한다.
- 동영상 decoding은 사용 환경의 OpenCV codec 지원 범위에 따른다.
- 초기 구현은 UI page 기반이며 저장/복원, video overlay pulse, keyframe tagging은 후속 확장 지점으로 남겼다.
