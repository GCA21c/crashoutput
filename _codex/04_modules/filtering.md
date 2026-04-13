# Filtering module

이 문서는 filtering 동작의 개요만 다룬다.
RAW reference 정의와 baseline 규칙은 반드시 `raw_reference_policy.md`를 따른다.

## 역할
- CFC filtering 수행
- target class 적용
- 필요한 helper channel 생성 여부 판단

## 핵심 원칙
- 이미 필터링된 채널의 의도적 재필터링 금지
- target CFC가 없을 때 raw reference 기준으로만 재구축
- 원채널 직접 사용이 가능하면 파생 채널 최소화

## 점검 포인트
- 입력 채널 lineage가 명확한가
- helper channel이 raw-based인가
- naming convention이 유지되는가
- injury path와 preprocessing path가 같은 기준을 보는가
