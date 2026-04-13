# AGENTS

이 저장소에서 Codex는 아래 순서로만 문서를 읽고 작업한다.

## 시작 순서
1. 이 파일을 먼저 읽는다.
2. `_codex/02_rules/dev_rules.md`를 읽는다.
3. 요청에 맞는 `_codex/03_workflows/` 및 `_codex/04_modules/` 문서를 읽는다.
4. 필요한 코드 파일만 최소 범위로 확인한다.

## 절대 규칙
- 코드 수정은 사용자 요청 범위 안에서만 한다.
- 문서 정본은 `_codex/02_rules/dev_rules.md`이다.
- 절차 정본은 `_codex/03_workflows/codex_workflow.md`이다.
- RAW reference 기준 정본은 `_codex/04_modules/raw_reference_policy.md`이다.
- 이미 필터링된 채널의 의도적 재필터링은 금지한다.
- 파생 채널은 꼭 필요할 때만 만든다.
- `_codex/` 문서를 `app/` 아래로 이동하지 않는다.

## 외부 참조
- crash 규정, 계산식, 필터링 기준, 평가 기준을 건드릴 때는 `crash-reference` MCP를 우선 사용한다.
- 사용자가 `소스자료`라고 말하면 동일하게 `crash-reference` 참조 흐름으로 처리한다.

## 문서 읽기 경로
- 규칙: `_codex/02_rules/dev_rules.md`
- 절차: `_codex/03_workflows/codex_workflow.md`
- 아키텍처: `_codex/01_architecture/system_map.md`
- 모듈 정책: `_codex/04_modules/`
- 파일 책임: `_codex/05_reference/file_to_responsibility_map.md`
