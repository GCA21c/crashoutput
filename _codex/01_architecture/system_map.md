# System map

## Runtime structure
- `main.py` : process entry point
- `app/shell.py` : top-level shell / composition
- `app/ui/` : user-facing workflow and pages
- `app/services/` : loading, preprocessing, injury calculations
- `app/core/` : reusable domain logic, dummy profiles, ISO parsing, dataset storage, utilities

## High-level data flow
1. `app/services/io/`에서 데이터 로드
2. `app/core/io/dataset_store.py`에서 dataset/state 관리
3. `app/core/isocode/`와 `app/core/dummy/`에서 ISO grouping 및 dummy context 해석
4. `app/services/preprocessing/service.py`에서 preprocessing 수행
5. `app/services/injury/`에서 injury 계산
6. `app/ui/pages/`와 `app/ui/components/`에서 결과 표시 및 제어

## Architectural hotspots
### A. Multi-dummy hotspot
- ISO prefix B1~B6가 channel routing의 기준이다.
- dummy-set UI/state와 injury routing이 어긋나면 결과가 틀어진다.

### B. Filtering hotspot
- preprocessing service는 전체 결과에 영향을 주는 핵심 경계다.
- raw-source traceability가 편의성보다 우선이다.
- raw reference 기준은 별도 정본 문서로 관리한다.

### C. Injury hotspot
- `injury_page.py`는 UI orchestration 중심이다.
- 실제 계산은 `app/services/injury/*.py`에 분산되어 있다.
- 공통 계산 보조는 `common_engines.py`가 담당한다.

## Broad-review required
다음 파일을 건드리면 인접 모듈까지 넓게 본다.
- `app/services/preprocessing/service.py`
- `app/services/injury/common_engines.py`
- `app/ui/pages/injury_page.py`
- `app/ui/pages/dummy_set_page.py`
- `app/core/dummy/engine.py`
- `app/core/isocode/engine.py`
