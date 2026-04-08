# Repository layout

## Exact production paths in this project
```text
main.py
app/
├─ shell.py
├─ core/
│  ├─ dummy/
│  ├─ io/
│  ├─ isocode/
│  └─ utils/
├─ services/
│  ├─ injury/
│  ├─ io/
│  └─ preprocessing/
└─ ui/
   ├─ components/
   ├─ pages/
   └─ viewer_module.py
```

## Codex documentation paths to add
```text
AGENTS.md
_codex/
├─ 00_project/
├─ 01_architecture/
├─ 02_rules/
├─ 03_workflows/
├─ 04_modules/
├─ 05_reference/
├─ 06_templates/
├─ 07_handoffs/
└─ 08_change_logs/
```

## Separation rule
- Code lives in `main.py` and `app/`
- Operational knowledge for Codex lives in `_codex/`
- Root `AGENTS.md` is the single entry point that tells Codex what to read first
