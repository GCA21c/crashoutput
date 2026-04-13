# Import guide

이 패키지는 **기존 프로그램 저장소 루트**에 그대로 푼다.

## 저장소 루트에 이미 있어야 하는 것
- `main.py`
- `app/`

## 압축 해제 후 기대 구조
```text
project_root/
├─ main.py
├─ app/
├─ AGENTS.md
└─ _codex/
```

## 배치 규칙
- `AGENTS.md`는 반드시 저장소 루트에 둔다.
- `_codex/`는 반드시 `app/`와 분리한다.
- `_codex/`를 `app/` 안으로 이동하지 않는다.
- Codex는 `project_root/`에서 연다.

## 우선 확인
- 루트에서 `AGENTS.md`가 보이는지 확인
- `_codex/02_rules/dev_rules.md`가 보이는지 확인
- `_codex/03_workflows/codex_workflow.md`가 보이는지 확인
