# Current Handoff

이 문서는 현재 작업 상태를 다시 이어가기 위한 임시 handoff다.
필요 없으면 이 파일만 삭제하면 된다.

## 현재 작업 기준
- 현재 작업 루트는 아래 경로다.
  - `/Users/gca_mac/Desktop/workspace/crashoutput`
- 이제 `v09x/` 하위 구조는 제거했고, 코드와 `.git`은 모두 루트로 이동했다.
- git repo는 루트 하나만 사용한다.

## 현재 git 상태
- 로컬 브랜치
  - `main`
  - `v091`
  - `v095`
- 세 브랜치는 현재 모두 같은 커밋을 가리킨다.
  - `40963f4` `결과요약 표시오류 수정2`
- 원격 repo
  - `origin = https://github.com/GCA21c/crashoutput.git`
- 원격 브랜치
  - `origin/main`
  - `origin/v091`
  - `origin/v095`

## 최근 중요 변경
- DAT loader `215=-1` blanket 치환 제거
  - raw import 단계에서 `-1 -> 0`으로 바꾸던 동작 제거
- Neck `MOCy` 공식 수정
  - `MOCy = My - (Fx * D)`
- Neck 출력 부호 정책 수정
  - `Peak Extension MOCy` 강제 양수 제거
  - `Peak Comp. Force (FZ-)` 강제 양수 제거
- Neck 결과요약 라벨 수정
  - `Fx`
    - `MAX(Rear Shear)`
    - `MIN(Forward Shear)`
  - `Fz`
    - `MAX(Tension)`
    - `MIN(Compression)`
  - `My`
    - `MAX(Flexion)`
    - `MIN(Extension)`
- 가속도 결과 단위 정리
  - HEAD / CHEST / PELVIS 결과 단위는 `g`
- `High-Resolution 3ms Search` 기본값
  - HEAD / CHEST / PELVIS에서 기본 해제

## 문서 운용 기준
- 공통 규칙과 실제 작업 문서는 현재 이 repo의 `_codex/`를 기준으로 본다.
- 루트 바깥 공통 Codex 문서는 제거했다.
- 지금은 이 repo 하나만 보면 된다.

## 다음 재개 시 권장 순서
1. 이 handoff 문서를 읽는다.
2. `_codex/02_rules/dev_rules.md`를 읽는다.
3. `_codex/03_workflows/codex_workflow.md`를 읽는다.
4. 요청과 직접 관련된 `_codex/04_modules/` 문서를 읽는다.
5. 필요한 코드만 최소 범위로 확인하고 작업한다.

## 정리 메모
- 이 handoff는 resume 안정화를 위한 임시 파일이다.
- 작업 흐름이 안정되면 삭제해도 된다.
