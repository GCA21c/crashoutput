# Video Analysis RAM preload

## What changed
- `app/ui/pages/video_analysis_page.py`에 video load 단계의 RAM preload 경로를 추가했다.
- 대상 video는 기본적으로 전체 frame을 OpenCV로 순차 decode해 memory list에 보관한다.
- preload 성공 slot은 frame 표시 시 OpenCV seek/read, background prefetch, playback buffer refill을 건너뛰고 RAM frame만 직접 조회한다.
- preload 완료 후 OpenCV capture를 release해 원본 video file/network handle을 유지하지 않는다.
- file size가 `1GB` 이상이면 preload 진행 전 사용자 확인 경고를 띄운다.
- preload 중에는 main window 위에 `VIDEO LOAD` overlay와 progress bar를 표시한다.

## Why
- Video Analysis에서 keyframe drag, frame step, playback이 OpenCV random seek 병목을 반복적으로 타며 체감 끊김이 발생했다.
- 사용 영상이 짧고 RAM 여유가 있는 조건에서는 decode frame을 memory에 올려 두는 방식이 가장 직접적인 개선 경로다.

## Scope / risk
- 기존 injury/report/export/data loading 계산 로직은 변경하지 않았다.
- decode가 중간 실패하면 해당 video는 로드하지 않는다.
- decoded frame list는 메모리를 크게 사용할 수 있으므로 clear/reset 시 해제되도록 했다.
- 현재 검증은 macOS 개발 환경의 import/문법 수준이며, Windows exe 환경에서는 실제 고속 영상 load/play 테스트가 필요하다.
