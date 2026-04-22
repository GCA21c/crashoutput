# System map

## Runtime structure
- `main.py` : process entry point
- `app/shell.py` : top-level shell / composition
- `app/ui/` : user-facing workflow and pages
- `app/services/` : loading, preprocessing, injury calculations
- `app/core/` : reusable domain logic, dummy profiles, ISO parsing, dataset storage, utilities
- `app/report/` : report snapshot, plotting, formatter, export

## High-level data flow
1. `app/services/io/`에서 데이터 로드
2. `app/core/io/dataset_store.py`에서 dataset/state 관리
3. `app/core/isocode/`와 `app/core/dummy/`에서 ISO grouping 및 dummy context 해석
4. `app/services/preprocessing/service.py`에서 preprocessing 수행
5. `app/services/injury/`에서 injury 계산
6. `metadata["injury_saved_results"]`에 canonical payload store 반영
7. `app/report/`와 `app/ui/pages/`에서 결과 표시, snapshot, plotting, export 수행

## Architectural hotspots
### A. Multi-dummy hotspot
- ISO prefix B1~B6가 channel routing의 기준이다.
- TEST SETUP UI/state와 injury/filtering routing이 어긋나면 결과가 틀어진다.

### B. Filtering hotspot
- preprocessing service는 전체 결과에 영향을 주는 핵심 경계다.
- raw-source traceability가 편의성보다 우선이다.
- raw reference 기준은 별도 정본 문서로 관리한다.

### C. Injury hotspot
- `injury_page.py`는 UI orchestration 중심이다.
- 실제 계산은 `app/services/injury/*.py`에 분산되어 있다.
- 공통 계산 보조는 `common_engines.py`가 담당한다.
- 현재 결과 정본은 `injury_saved_results` canonical payload store 쪽으로 이동 중이다.
- `canonical_metrics`, `canonical_graphs`, `calculation_context`가 다음 formatter/report 경계의 기준이다.

### D. Report / plotting hotspot
- `app/report/engine.py`는 SUMMARY REPORT snapshot 추출 경계다.
- `app/report/plotting_service.py`는 graph list, graph text, PPT export 입력 조립 경계다.
- `app/report/formatters/`는 canonical payload accessor와 formatter 공통 규칙을 수용하는 계층이다.
- `report_values`, `metric_extrema`, `summary_text`는 아직 compatibility/cache 역할로 남아 있다.

## Broad-review required
다음 파일을 건드리면 인접 모듈까지 넓게 본다.
- `app/services/preprocessing/service.py`
- `app/services/injury/common_engines.py`
- `app/ui/pages/injury_page.py`
- `app/report/engine.py`
- `app/report/plotting_service.py`
- `app/services/state/injury_result_store.py`
- `app/services/state/injury_metric_canonical.py`
- `app/ui/pages/test_setup_page.py`
- `app/core/dummy/engine.py`
- `app/core/isocode/engine.py`
