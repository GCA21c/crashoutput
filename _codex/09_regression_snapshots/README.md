# Regression snapshots

이 폴더는 Phase 5 이후 고위험 리팩토링 전에 만드는 비교 기준을 둔다.

규칙:
- 원본 시험 데이터 전체를 저장하지 않는다.
- 저장 `.pkl`에서 구조, 채널 digest, report snapshot, saved summary contract만 캡처한다.
- 실제 대표 데이터 snapshot JSON은 필요할 때만 생성하고, 민감 데이터 여부를 확인한 뒤 보관한다.
- refactor 전후 snapshot 차이가 있으면 계산/저장/리포트 contract 변경으로 보고 원인을 먼저 확인한다.

기본 생성 명령:

```bash
python3 tools/capture_regression_snapshot.py capture path/to/sample.pkl
```

비교 명령:

```bash
python3 tools/capture_regression_snapshot.py compare before.json after.json
```
