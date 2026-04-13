# 2026-04-13 codex doc refactor phase2

## What changed
- AGENTS를 진입 순서 + 문서 우선순위 중심으로 재정리했다.
- dev_rules를 규칙 정본으로 명시했다.
- codex_workflow를 절차 정본으로 정리하고 MCP 사용 시점을 분리했다.
- project_overview / repo_layout / system_map / filtering / file_to_responsibility_map의 역할 겹침을 줄였다.
- import guide를 즉시 배치 가능한 형태로 다듬었다.

## Why
- Codex가 같은 규칙을 여러 문서에서 반복 해석하지 않게 하기 위함.
- 문서 간 우선순위 충돌을 줄이고 토큰 낭비를 줄이기 위함.
- 실사용 시 바로 올려도 문서 경로와 판단 기준이 흔들리지 않게 하기 위함.

## Impacted files
- `AGENTS.md`
- `README_IMPORT.md`
- `_codex/00_project/project_overview.md`
- `_codex/00_project/repo_layout.md`
- `_codex/01_architecture/system_map.md`
- `_codex/02_rules/dev_rules.md`
- `_codex/03_workflows/codex_workflow.md`
- `_codex/04_modules/filtering.md`
- `_codex/05_reference/file_to_responsibility_map.md`

## Regression risks
- 없음. 문서만 수정했고 코드는 건드리지 않았다.

## Next checks
- 실제 Codex 세션에서 AGENTS -> dev_rules -> workflow -> module docs 순서로 읽는지 확인.
- 사용자가 규정/기준 변경을 요청할 때 crash-reference MCP를 우선 참조하는지 확인.
