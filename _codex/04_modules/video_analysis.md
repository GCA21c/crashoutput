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
- Reset 버튼으로 동영상, pulse channel, sync/keyframe 상태를 초기화한다.
- OpenCV `VideoCapture`로 현재 frame만 seek/read 한다.
- 두 영상은 첫 번째 영상 fps를 master metadata로 사용한다.
- fps가 다르면 사용자 경고를 띄운다.
- sync/pulse matching 기준은 fps 환산이 아니라 `1 video frame = 1 ms`이다.
- dataset channel은 기존 viewer의 `df`와 `time_column`을 참조한다.
- Pulse channel은 최대 3개까지 선택한다.
- `sync_frame_offset`은 frame 단위이며 음수 값을 허용한다.
- 표시 frame/time은 `raw_frame_index + sync_frame_offset` 기준이다.
- 예: offset `-50`이면 raw frame 0을 `-50ms`로 표시하고, raw frame 50이 test T0 / `0ms`가 된다.
- 데이터 pulse는 기존 dataset time 기준으로 `0ms`부터 시작하며, graph/timeline은 음수 offset만큼 데이터 앞 구간을 열어 표시한다.
- frame 이동 성능을 위해 현재 주변 frame만 메모리 cache에 유지한다.
- pulse graph는 channel 변경 시 전체 redraw하고, frame 이동 시에는 vertical cursor만 갱신한다.
- Left/Right key를 누르고 있으면 초기 1-frame 이동 후 반복 이동은 2-frame step으로 가속한다.
- key frame timeline은 drag-to-seek를 지원한다.
- Pulse graph legend는 움직이지 않도록 우측 상단에 고정한다.
- Pulse curve는 별도 큰 graph 영역 대신 video canvas 하단에 semi-transparent overlay로 표시한다.
- `Clear V1`, `Clear V2`로 각 video slot을 개별 제거할 수 있다.
- video가 1개만 로드된 경우 V2 영역을 숨기고 V1이 전체 video 영역을 사용한다.
- channel add는 toolbar의 상시 combobox에서 channel을 선택한 뒤 `Add channel` 버튼으로 추가한다.
- overlay 우측 상단에 pulse channel ISO code legend를 curve 색상과 같은 색으로 표시한다.
- overlay legend는 현재 cursor 지점의 channel value와 unit을 `ISOCODE value [unit]` 형식으로 표시한다.
- 별도 Pulse Overlay 목록 영역은 제거했고, pulse는 video overlay에만 표시한다.
- mouse wheel:
  - cursor가 video 영역에 있으면 video image zoom
  - cursor가 pulse overlay box 안에 있으면 pulse time-axis zoom
- drag pan:
  - 확대된 video 영역을 drag 하면 image pan
  - 확대된 pulse overlay box 안을 drag 하면 pulse time-window pan

## Placeholder / extension points
- Pulse overlay-on-video는 아직 분리 Pulse 영역으로만 구현되어 있다.
- Key frame 영역은 duration bar, current marker, keyframe placeholder 구조만 있다.
- keyframe/event tagging 저장 구조는 `VideoAnalysisState.keyframes`를 확장한다.
- 저장/복원은 아직 연결하지 않았고, 필요 시 기존 metadata/report cache 패턴에 맞춰 payload화한다.

## Dependency note
- `cv2`가 없으면 앱 import는 깨지지 않고, Video Load 시 OpenCV 설치 안내를 표시한다.
- Pillow가 있으면 `ImageTk`로 frame을 표시하고, 없으면 OpenCV PNG encode + Tk `PhotoImage` fallback을 시도한다.
