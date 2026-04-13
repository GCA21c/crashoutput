# Project overview

## Project type
Desktop Python crash-analysis tool with a UI-driven workflow.

## Production layout
- `main.py` : app launcher
- `app/core/` : core data/domain utilities
- `app/services/` : IO, preprocessing, injury logic
- `app/ui/` : pages, viewer orchestration, UI components

## Main goal
DIAdem-like crash-analysis workflow를 유지·확장한다.
중점 영역은 다음과 같다.
- filtering / preprocessing
- multi-dummy handling
- ISO-code based grouping
- injury computations
- traceable UI-driven analysis

## Repository assumptions
- 편집은 macOS 원격 개발 환경에서 수행될 수 있다.
- 최종 수동 검증은 Windows에서 이뤄질 수 있다.
- UI, path, font, icon, encoding, generated artifact의 cross-platform 차이를 항상 고려한다.
- 민감한 환경 정보는 문서에 기록하지 않는다.
