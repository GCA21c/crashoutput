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
- video slot layout 변경 직후 실제 canvas size가 확정된 다음 frame을 다시 렌더링하도록 post-layout refresh를 추가했다. 2개 video 동시 load 시 V2가 초기 작은 크기로 표시되는 현상을 방지한다.
- selected pulse channel별 absolute peak 위치를 계산하고, View 1/2에서는 pulse line과 같은 색상의 vertical solid line으로 overlay에 표시한다.
- video slot을 V1/V2 고정 배열로 바꿔 `Clear V1` 후에도 V2가 V1으로 당겨지지 않게 했다. 단독 video 표시 시 남아 있는 slot viewer가 전체폭을 사용한다.
- `Pulse View 3`을 추가했다. View 2 스타일을 기반으로 현재 video time까지 pulse line을 누적 표시하고, frame cursor line 대신 peak point marker를 표시한다.
- View 3 redraw 부하를 줄이기 위해 view range별 sampled pulse point cache를 추가했다.
- playback speed selector를 `x0.5`, `x1.0`, `x2.0` 구성으로 정리했다. 배율은 frame skip이 아니라 timer delay에 반영하며, 각 tick은 1 frame씩 진행한다.
- video playback 1차 리팩토링을 적용했다. Frame cache를 `FrameCache`로 분리하고, 순차 재생 중 가능한 경우 `capture.set()` seek 없이 `read()`를 이어간다.
- video playback 2차 리팩토링을 적용했다. slot별 background prefetch worker가 별도 `VideoCapture`로 주변 raw frame을 `FrameCache`에 미리 채우고, Tk UI thread는 cache 조회와 표시를 담당한다.
- x1.0 체감 저하 가능성 때문에 full 양방향 background prefetch는 기본 OFF로 둔다.
- pulse channel base snapshot을 추가해 frame 이동 중 overlay payload 전체 재구성을 줄였다.
- slot/frame/image size/zoom 기준 PhotoImage cache를 추가해 같은 표시 조건에서 RGB 변환/resize/PhotoImage 재생성을 줄였다.
- video canvas item을 재사용하도록 변경했다. frame 이동 시 전체 canvas delete 대신 video image item을 갱신한다.
- Pulse View 1/2는 curve/peak/T0/background static layer를 유지하고, frame 이동 시 current cursor/time/legend value만 `pulse_dynamic` layer로 갱신한다.
- 재생 중에는 video/status/pulse/keyframe timeline을 즉시 갱신한다.
- keyframe timeline drag는 cursor marker만 즉시 갱신하고, video seek는 33ms throttle로 마지막 drag 위치를 반영한다. drag release 시에는 최종 위치를 즉시 반영한다.
- keyframe timeline drag/label/seek 값을 `1 frame = 1 ms` 기준의 정수 ms로 snap한다.
- 공통 RAM segment buffer를 현재 frame 기준 뒤쪽 50ms, 앞쪽 200ms로 정리했다. 수동 frame step/keyframe/first/last seek와 자동재생이 같은 raw frame cache를 우선 사용한다.
- segment prefetch는 현재 frame 이후 구간을 먼저 채우고, 그 다음 뒤쪽 구간을 채운다.
- 재생 중 forward prefetch는 체감상 방해 가능성이 있어 제거했다. 자동재생은 순차 read 최적화 경로를 우선한다.
- 자동재생용 순차 read-ahead buffer를 추가했다. 별도 worker/capture를 쓰지 않고 UI capture로 현재 frame 이후 +12 frame을 idle에서 최대 3 frame씩 채운다.
- PhotoImage idle prebuild는 체감 효과가 낮아 제거했다.
- 단독 video layout에서는 현재 보이는 viewer만 pulse overlay를 갱신하고, 숨겨진 viewer의 placeholder redraw를 피한다.
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
