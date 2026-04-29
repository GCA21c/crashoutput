# Video Analysis initial build

## What changed
- `ANALYSIS > VIDEO ANALYSIS` 신규 메뉴와 페이지를 추가했다.
- OpenCV 기반 video load, 최대 2개 video slot, frame step/play/pause, sync frame offset 표시를 구현했다.
- 기존 viewer dataset channel을 최대 3개까지 pulse graph에 추가하고 video frame cursor와 연동한다.
- Key frame timeline은 duration bar/current marker/keyframe placeholder로 초기 구축했다.
- Reset 버튼으로 video/pulse/sync/keyframe 상태를 초기화한다.
- 재생 중 image label이 레이아웃을 밀지 않도록 video frame 표시를 고정 Canvas 방식으로 변경했다.
- sync 기준을 `1 video frame = 1 ms`로 정리하고, offset `-50` 입력 시 raw frame 0을 `-50ms`, raw frame 50을 test T0로 표시한다.
- pulse graph cursor-only update, 작은 frame cache, Left/Right key hold 2-frame 가속, key frame timeline drag seek를 추가했다.
- 데이터 pulse 앞에 음수 video offset 구간을 열어 표시하고, pulse legend를 우측 상단으로 고정했다.
- Key frame timeline을 dark editor-style track, progress fill, cursor pill, diamond keyframe marker 형태로 정리했다.
- Pulse graph를 별도 큰 영역에서 video canvas 하단 semi-transparent overlay로 옮기고, `Clear V1`/`Clear V2` 개별 video clear 버튼을 추가했다.
- 1-video layout은 V1 단독 전체폭으로 표시하고, channel add는 toolbar combobox + button 방식으로 변경했다.
- pulse overlay 우측 상단에 channel ISO code legend를 curve 색상과 동일하게 표시한다.
- overlay legend에 현재 cursor 지점의 channel value/unit을 표시하고, 별도 Pulse Overlay 목록 영역을 제거했다.
- video overlay pulse curve 두께를 낮춰 시야 방해를 줄였다.
- mouse wheel zoom을 추가했다. cursor가 video 영역이면 video zoom, pulse overlay box 안이면 pulse time-axis zoom으로 분기한다. pan은 제외했다.
- 확대 상태에서 drag pan을 추가했다. video 영역 drag는 image pan, pulse overlay box drag는 pulse time-window pan으로 동작한다.
- Reset 버튼은 Yes/No 확인 팝업을 거친 뒤 초기화한다.
- pulse overlay background와 foreground layer tag를 분리했다. pulse line/time/legend/T0/current cursor는 항상 background보다 위에 표시한다.
- 하단 안내문구 우측에 `Pulse View 1` / `Pulse View 2` 선택 버튼을 추가했다.
- `Pulse View 1`은 4면 outline이 모두 있는 반투명 pulse box 스타일이고, `Pulse View 2`는 pulse box background 없이 하단 line만 표시하는 readability 강화 스타일이다.
- 다음 최적화 방향은 `_codex/04_modules/video_analysis.md`의 `Next optimization work`에 정리했다.

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
- 초기 구현은 UI page 기반이며 저장/복원, background decode, keyframe tagging은 후속 확장 지점으로 남겼다.
