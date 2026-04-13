# Codex workflow

이 문서는 **절차 정본**이다.
규칙 내용은 `_codex/02_rules/dev_rules.md`를 따른다.

## 기본 작업 순서
1. 저장소 루트에서 시작한다.
2. 루트 `AGENTS.md`를 읽는다.
3. `_codex/02_rules/dev_rules.md`를 읽는다.
4. 요청과 직접 관련된 `_codex/04_modules/` 문서를 읽는다.
5. 관련 코드 파일만 최소 범위로 확인한다.
6. 수정 전 side effect 가능성이 있는 인접 파일을 짚는다.
7. 최소 수정으로 반영한다.
8. material change면 change log를 남긴다.

## crash-reference MCP 사용 시점
다음 경우에는 `crash-reference`를 먼저 확인한다.
- crash criteria 계산식 변경
- filtering / CFC 기준 변경
- rating / threshold / regulation 반영
- 사용자가 `소스자료`, 규정, 기준, 법규, NCAP 근거를 요구한 경우

## Bug fix 절차
- page -> service -> core 경계를 따라 원인 위치를 좁힌다.
- state owner와 computation owner를 분리해서 본다.
- shared helper를 먼저 확인한 뒤 패치한다.

## Feature change 절차
- UI-only / service-only / cross-layer 중 어디인지 먼저 정한다.
- 명시 요구가 없으면 기존 data flow를 유지한다.
- 아키텍처 계약이 바뀌면 관련 문서를 함께 갱신한다.

## 종료 전 점검
- adjacent module side effect
- naming consistency
- raw reference / filtering 충돌 여부
- Windows 기준 path, font, icon, encoding 리스크
