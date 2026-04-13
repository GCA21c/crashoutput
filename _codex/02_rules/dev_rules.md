# Development rules

이 문서는 Codex 작업 규칙의 **정본(single source of truth)** 이다.
다른 문서와 표현 차이가 있으면 이 문서를 우선한다.

## 1. 작업 범위 규칙
- 사용자가 요구한 범위만 수정한다.
- 가장 작은 안정 단위로 수정한다.
- 파일, 모듈, 공개 UI 문구는 요구가 없으면 바꾸지 않는다.
- `_codex/` 문서를 `app/` 안으로 옮기지 않는다.

## 2. 데이터 무결성 규칙
- 항상 raw-source provenance를 우선한다.
- 이미 필터링된 채널을 의도적으로 다시 필터링하지 않는다.
- helper/derived channel을 만들기 전 raw 기반인지 derived 기반인지 먼저 확인한다.
- 필터링된 원채널을 직접 사용할 수 있으면 불필요한 파생 채널 생성을 피한다.

## 3. RAW reference 규칙
- `raw reference`의 정식 정의는 `_codex/04_modules/raw_reference_policy.md`를 따른다.
- target CFC가 없을 때 재구축 기준은 `pre_filter_reference_df`이다.
- trimming은 raw reference baseline을 다시 정의하면 안 된다.
- offset 적용 이후, filtering/trimming 이전 상태를 기준으로 본다.

## 4. 네이밍 / 일관성 규칙
- 기존 channel/result naming convention을 유지한다.
- UI label, 저장 key, 생성 채널 이름은 서로 어긋나지 않게 맞춘다.
- 더미 이름 표시는 고정 위치코드인지 사용자 입력 이름인지 먼저 확인한다.

## 5. 멀티더미 규칙
- ISO prefix grouping을 1급 라우팅 키로 취급한다.
- B1~B6 렌더링 및 상태 보존에 영향이 없는지 확인한다.
- 더미 팩터가 필요한 상해 계산은 dummy-set 설정값을 실제로 참조하는지 확인한다.

## 6. 공유 엔진 규칙
- 한 상해 모듈을 수정하기 전에 `common_engines.py`와 인접 injury module 결합 여부를 먼저 본다.
- UI page를 수정하기 전에 `app/ui/components/` 계약을 먼저 본다.
- preprocessing 변경은 전체 상해 결과에 영향을 줄 수 있다고 가정한다.

## 7. 환경 규칙
- 개발 환경과 최종 검증 환경이 다를 수 있다고 가정한다.
- path, text encoding, icon loading, font, Tk, matplotlib는 cross-platform 리스크로 본다.
- 민감한 환경 정보(IP, 내부 네트워크명, 사설 접근 경로)는 문서에 남기지 않는다.
- 현재 호스트 OS에서만 테스트했다면 Windows 검증 리스크를 로그에 남긴다.

## 8. 문서 / 로그 규칙
- material change가 있으면 `_codex/08_change_logs/`에 짧은 로그를 남긴다.
- 로그에는 무엇을, 왜, 어디를, 어떤 리스크가 있는지 적는다.
- 코드 규칙과 절차 규칙은 로그에 다시 길게 복제하지 않는다.
