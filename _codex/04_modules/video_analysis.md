# Video analysis module

## Main code paths
- `app/ui/pages/video_analysis_page.py`
- `app/ui/components/video_viewer.py`
- `app/ui/components/pulse_timeline.py`
- `app/core/video/video_sync.py`

## Current role
- 고속 동영상과 로드된 dataset channel pulse를 frame/time 기준으로 같이 확인하는 초기 UI다.
- 기존 injury/report/export 계산 경로와 payload 저장 구조는 건드리지 않는다.
- `ANALYSIS > VIDEO ANALYSIS` 메뉴로 진입한다.

## Current implementation
- 동영상은 최대 2개까지 로드한다.
- video slot은 V1/V2 고정 슬롯으로 관리한다. V1을 clear해도 V2는 V1으로 당겨지지 않는다.
- Reset 버튼은 Yes/No 확인 후 동영상, pulse channel, sync/keyframe 상태를 초기화한다.
- `UI 확장` 버튼은 Video Analysis 전용 compact mode를 토글한다.
- compact mode에서는 좌측 navigation, 상단 file/status bar, 하단 Processing History를 숨기고 Video Analysis 화면 영역을 확장한다.
- `UI 축소` 또는 다른 page 이동 시 compact mode를 해제하고 shell layout을 복원한다.
- `Video Load` 클릭 시 `Normal Mode` / `Boost Mode`를 먼저 선택한다.
- `Normal Mode`는 기존 OpenCV streaming/cache/prefetch 경로를 사용한다.
- `Boost Mode`는 전체 frame을 RAM에 preload한다.
- `Boost Mode` preload 성공 slot은 seek/step/play에서 OpenCV seek/read 대신 RAM frame list만 사용한다.
- `Boost Mode` preload 완료 후에는 OpenCV capture를 release해 원본 video file/network handle을 유지하지 않는다.
- `Boost Mode`에서 video file이 `1GB` 이상이면 preload 진행 전 사용자 확인 경고를 띄운다.
- `Boost Mode` preload 실패 시 해당 video는 로드하지 않는다.
- 두 영상은 첫 번째 영상 fps를 master metadata로 사용한다.
- fps가 다르면 사용자 경고를 띄운다.
- sync/pulse matching 기준은 fps 환산이 아니라 `1 video frame = 1 ms`이다.
- dataset channel은 기존 viewer의 `df`와 `time_column`을 참조한다.
- Pulse channel은 최대 3개까지 선택한다.
- `sync_frame_offset`은 frame 단위이며 음수 값을 허용한다.
- 표시 frame/time은 `raw_frame_index + sync_frame_offset` 기준이다.
- 예: offset `-50`이면 raw frame 0을 `-50ms`로 표시하고, raw frame 50이 test T0 / `0ms`가 된다.
- 데이터 pulse는 기존 dataset time 기준으로 `0ms`부터 시작하며, graph/timeline은 음수 offset만큼 데이터 앞 구간을 열어 표시한다.
- video overlay pulse의 x-axis 표시 범위는 video time range를 기준으로 한다. 예: offset `-50`, frame_count `700`이면 overlay range는 `-50ms ~ 649ms`이고, 데이터 시간이 더 길어도 overlay 기본 범위를 늘리지 않는다.
- key frame timeline은 전체 확인을 위해 video range와 data range를 모두 포함한다. overlay와 visual scale은 다를 수 있지만, cursor/time 값은 동일한 `synced_time_ms`를 사용한다.
- 데이터 time 값 자체는 sync/overlay 표시를 위해 변경하지 않는다.
- frame 이동 성능을 위해 현재 주변 frame만 메모리 cache에 유지한다.
- preload된 video는 clear/reset 시 RAM frame list를 해제한다.
- frame cache는 `app/core/video/frame_cache.py`의 `FrameCache`로 분리했다.
- 공통 RAM segment buffer는 현재 frame 기준 뒤쪽 50ms, 앞쪽 200ms를 유지한다.
- 수동 frame step, keyframe seek, first/last 이동 후에는 같은 segment buffer를 background prefetch로 준비한다.
- segment prefetch는 현재 frame 이후 구간을 먼저 채우고, 그 다음 뒤쪽 구간을 채운다.
- 재생 중 prefetch는 기본 OFF로 둔다. 현재 자동재생은 순차 read 최적화 경로를 우선한다.
- 순차 재생 중에는 가능한 경우 매 frame `capture.set(CAP_PROP_POS_FRAMES)`를 호출하지 않고 현재 capture 위치에서 `read()`를 이어간다. seek/timeline/key step은 capture 위치를 reset한다.
- 자동재생은 별도 worker/capture prefetch 대신 UI capture의 순차 read-ahead buffer를 사용한다. 기본 buffer는 현재 frame 이후 +12 frame이고, idle refill은 한 번에 최대 3 frame씩 채운다.
- slot별 `FramePrefetchManager`를 추가했다. worker는 UI capture와 별도 `VideoCapture`를 소유하고 현재 frame 주변 raw frame을 `FrameCache`에 미리 채운다.
- full 양방향 prefetch worker 옵션은 x1.0 체감 저하 가능성이 있어 기본 OFF(`_prefetch_enabled = False`)로 둔다.
- worker는 Tk widget/PhotoImage를 만들지 않는다. UI update와 image object 생성은 계속 main thread에서 수행한다.
- Pulse View 1/2는 channel 변경/zoom/pan 시 static pulse layer를 다시 그리고, frame 이동 시에는 current cursor/time/legend value만 갱신한다.
- Left/Right key를 누르고 있으면 초기 1-frame 이동 후 반복 이동은 2-frame step으로 가속한다.
- playback speed selector는 `x0.3`, `x1.0`, `x2.5`를 제공한다. 배율은 frame skip이 아니라 timer delay에 반영하며, 각 tick은 1 frame씩 진행한다. frame/time 계산은 기존 `1 frame = 1 ms` 기준을 유지한다.
- key frame timeline은 drag-to-seek를 지원한다.
- key frame timeline drag/label/seek 값은 `1 frame = 1 ms` 기준에 맞춰 정수 ms로 snap한다.
- Pulse graph legend는 움직이지 않도록 우측 상단에 고정한다.
- Pulse curve는 별도 큰 graph 영역 대신 video canvas 하단에 semi-transparent overlay로 표시한다.
- `Clear V1`, `Clear V2`로 각 video slot을 개별 제거할 수 있다.
- video가 1개만 로드된 경우 해당 slot viewer만 전체 video 영역을 사용한다. 예: V1 clear 후 V2만 남으면 VIDEO 2가 단독 전체폭으로 표시된다.
- channel add는 toolbar의 상시 combobox에서 channel을 선택한 뒤 `Add channel` 버튼으로 추가한다.
- overlay 우측 상단에 pulse channel ISO code legend를 curve 색상과 같은 색으로 표시한다.
- overlay legend는 현재 cursor 지점의 channel value와 unit을 `ISOCODE value [unit]` 형식으로 표시한다.
- 선택된 각 pulse channel은 해당 채널 값의 absolute peak 지점을 계산해 View 1/2에서는 pulse line과 같은 색상의 vertical solid line으로 표시한다.
- 별도 Pulse Overlay 목록 영역은 제거했고, pulse는 video overlay에만 표시한다.
- 하단 안내문구 우측에 `Pulse View 1` / `Pulse View 2` 선택 버튼을 둔다.
- `Pulse View 1`은 기존 방식처럼 선택된 pulse curve 전체를 먼저 표시하고 current frame cursor를 함께 보여준다.
- `Pulse View 2`는 현재 video time까지 pulse curve가 시간 진행에 따라 생성되는 방식이다. frame cursor line은 표시하지 않고, peak가 지나간 뒤 같은 색상의 point marker로 표시한다.
- `BG ON` / `BG OFF` 버튼으로 pulse box, time, legend 배경 표시를 독립 제어한다.
- `BG ON`은 `resources/video/pulse_overlay_bg.png`의 검정 반투명 texture를 pulse box 크기에 맞춰 표시한다.
- `Tone Dark` / `Tone Light` 버튼으로 검정 반투명 계열과 흰색 반투명 계열 배경 texture를 선택한다.
- pulse overlay layer 규칙:
  - pulse box/background는 video 위, pulse line/text 아래에 먼저 그린다.
  - `pulse_fg`, `pulse_legend_text`는 항상 앞으로 올린다.
  - pulse curve, time text, T0 line, current cursor, legend text는 background/stipple에 가려지면 안 된다.
- mouse wheel:
  - cursor가 video 영역에 있으면 video image zoom
  - cursor가 pulse overlay box 안에 있으면 pulse time-axis zoom
- drag pan:
  - 확대된 video 영역을 drag 하면 image pan
  - 확대된 pulse overlay box 안을 drag 하면 pulse time-window pan

## Placeholder / extension points
- Pulse overlay-on-video는 현재 video canvas 하단 overlay로 구현되어 있고, 필요하면 향후 완전 overlay/opacity control panel로 확장한다.
- Key frame 영역은 duration bar, current marker, keyframe placeholder 구조만 있다.
- keyframe/event tagging 저장 구조는 `VideoAnalysisState.keyframes`를 확장한다.
- 저장/복원은 아직 연결하지 않았고, 필요 시 기존 metadata/report cache 패턴에 맞춰 payload화한다.

## Next optimization work
- Frame decode/cache 최적화:
  - 1차로 `FrameCache` 분리와 순차 read 최적화, frame-skip 배속을 적용했다.
  - 2차로 slot별 background prefetch worker를 적용했다.
  - 단, Tk widget 업데이트는 main thread에서만 수행한다.
- Playback responsiveness:
  - 재생 중에는 video/status/pulse/keyframe timeline을 즉시 갱신한다.
  - keyframe timeline drag는 cursor marker만 즉시 갱신하고, video seek는 33ms throttle로 마지막 drag 위치를 반영한다.
  - keyframe timeline drag release 시에는 pending seek를 취소하고 최종 위치를 즉시 반영한다.
  - 현재 화면에 보이는 video viewer만 pulse overlay를 갱신한다. 숨겨진 V1/V2 viewer는 재생 중 불필요한 placeholder/pulse redraw를 피한다.
- PhotoImage conversion 최적화:
  - raw frame cache와 별도로 slot/frame/image size/zoom 기준 PhotoImage cache를 추가했다.
  - zoom 변경, layout resize, clear/reset/load 시 관련 cache를 무효화한다.
  - Tk PhotoImage 객체 생성은 여전히 main thread에서 수행한다.
- Canvas redraw 최적화:
  - video background/image canvas item은 유지하고, frame 변경 시 `itemconfigure(image=...)`와 `coords(...)`로 갱신한다.
  - placeholder 전환은 잔상 방지를 위해 전체 delete를 유지한다.
  - Pulse View 1은 curve/peak/T0/background를 static layer로 유지하고, frame 이동 시 current cursor/time/legend value만 `pulse_dynamic` tag로 갱신한다.
  - Pulse View 2는 cursor time에 따라 curve 자체가 자라므로 current cursor 변화 시 pulse overlay를 다시 그린다.
- Pulse rendering 최적화:
  - channel 추가/zoom/pan 때만 Pulse View 1/2의 pulse curve points를 재계산하고, frame 이동 때는 current cursor/time/legend value만 갱신한다.
  - 큰 DAT channel에서는 downsampling/window sampling을 view range 기준으로 캐시한다.
  - 1차로 pulse channel base snapshot을 분리해 frame 이동 시 channel payload 전체 재구성을 줄인다.
- Video zoom/pan 품질:
  - 현재 zoom은 viewer canvas 크기 기준 image thumbnail을 다시 만드는 방식이다.
  - 고해상도 영상에서 더 부드럽게 하려면 raw frame crop/resize 방식 또는 cached resized levels를 검토한다.
- Sync UX:
  - offset input 외에 T0 jump, current frame set as T0, offset +/- step 버튼을 추가할 수 있다.
  - offset은 계속 `1 frame = 1 ms` 기준을 유지한다.
- Keyframe/event tagging:
  - `VideoAnalysisState.keyframes`를 event object list로 확장한다.
  - 예: `{time_ms, raw_frame, label, note, color}`.
- Persistence:
  - Video path, sync offset, selected channels, pulse view mode, keyframes는 나중에 project/session payload에 저장 가능하다.
  - 동영상 binary 자체는 저장하지 않고 path/reference만 저장하는 방향이 안전하다.
- Background decode risk:
  - OpenCV capture object는 thread-safety가 제한적일 수 있으므로 slot별 worker/capture ownership을 명확히 해야 한다.
  - worker 도입 전에는 cancel/close/reset 시 capture release와 queue clear 순서를 먼저 설계한다.

## Dependency note
- `cv2`가 없으면 앱 import는 깨지지 않고, Video Load 시 OpenCV 설치 안내를 표시한다.
- Pillow가 있으면 `ImageTk`로 frame을 표시하고, 없으면 OpenCV PNG encode + Tk `PhotoImage` fallback을 시도한다.
