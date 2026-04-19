# Regression snapshot workflow

이 문서는 Phase 5 이상의 구조 분해 전에 계산 결과와 report/export contract를 지키기 위한
snapshot 절차를 정의한다.

## Scope
대표 저장 파일(`.pkl`)을 기준으로 아래 항목을 JSON으로 캡처한다.

- dataframe shape, column order, column digest
- metadata structure
- `shared_dummy_config`
- `injury_saved_results`
- `report_saved_results.summary_report`
- `build_report_snapshot(metadata, "FMVSS 208")`의 비교용 contract

raw time-series 값을 그대로 문서에 저장하지 않는다. 채널 값은 digest와 요약 통계로 비교한다.

## Tool
도구 위치:

- `tools/capture_regression_snapshot.py`

snapshot 생성:

```bash
python3 tools/capture_regression_snapshot.py capture path/to/sample.pkl
```

출력 기본 위치:

- `_codex/09_regression_snapshots/{sample_stem}_snapshot.json`

비교:

```bash
python3 tools/capture_regression_snapshot.py compare before.json after.json
```

## Required baseline set
Phase 5 high-risk refactor 전에는 가능하면 아래 케이스를 각각 저장한다.

1. 원본 로드 후 저장 파일
2. `_O` 저장 파일
3. `_O_F` 저장 파일
4. `_O_F_I` 또는 injury 계산이 완료된 저장 파일
5. REPORT SUMMARY `Valuation` 및 저장이 끝난 `_R` 파일

대표 더미 구성:

- B1 단일 더미
- B1/B3 또는 두 개 이상 더미
- FMVSS 208 / FRONTAL
- H3_50%M
- H3_5%F

## Must-match fields
무동작 변경 리팩토링에서는 아래 항목이 같아야 한다.

- dataframe column order
- dataframe per-column digest
- report snapshot slot order
- report snapshot row order
- `slot`, `slot_label`, `dummy_name`, `dummy_profile`
- `section_key`, `region`, `result_key`, `label`, `unit`
- `value`, `limit`, `status`, `comparison`
- `result_uid`, `value_source`, `value_path`, `limit_source`
- saved summary `report_fields`, `slots`, `rows`, `excel_mapping`

## Allowed differences
아래는 비교에서 직접 실패 원인으로 보지 않는다.

- snapshot 생성 시각
- snapshot source file absolute path
- 순수 문서 수정
- helper 위치 변경

## Stop condition
snapshot 차이가 있으면 다음 작업을 중단한다.

1. 차이 경로를 확인한다.
2. 계산 값 차이인지, 표시/문서 차이인지 분류한다.
3. 계산 값, report row order, payload key 차이면 원인 수정 전 다음 phase로 넘어가지 않는다.
4. 의도된 contract 변경이면 사용자 승인 후 문서와 change log에 기록한다.
