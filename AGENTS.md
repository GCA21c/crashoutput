# AGENTS.md

This repository is a Python crash-analysis application.

## Repository truth
- Production entry point: `main.py`
- Production code root: `app/`
- Project knowledge base for Codex: `_codex/`
- Do not create new markdown files inside `app/` unless explicitly requested.
- Keep code changes in `app/` and documentation updates in `_codex/`.

## First read order
1. `_codex/00_project/project_overview.md`
2. `_codex/00_project/repo_layout.md`
3. `_codex/01_architecture/system_map.md`
4. `_codex/02_rules/dev_rules.md`
5. `_codex/05_reference/file_to_responsibility_map.md`

## When the task touches a specific area
- Dummy configuration / multi-dummy UI: read `_codex/04_modules/dummy_set.md`
- Filtering / preprocessing: read `_codex/04_modules/filtering.md`
- Injury UI orchestration: read `_codex/04_modules/injury_ui.md`
- Head / neck / chest calculations: read `_codex/04_modules/injury_engines.md`
- ISO grouping / dummy routing: read `_codex/04_modules/isocode_and_dummy_profiles.md`

## Working rules
- Preserve the existing raw -> filter -> compute philosophy.
- Do not re-filter already filtered channels.
- Minimize unnecessary derived-channel creation.
- Prefer changing existing modules over duplicating logic.
- Keep naming consistent with current channel/result conventions.
- Respect multi-dummy architecture based on ISO prefixes such as B1~B6.
- When changing one injury module, review side effects on shared engines and UI state flow.

## Change discipline
- For meaningful code changes, update `_codex/08_change_logs/` with a short note.
- Record: changed files, reason, behavior impact, known risks, follow-up items.

## Completion standard
A task is not complete unless:
- the changed behavior matches the request,
- impacted module boundaries were reviewed,
- naming/state persistence side effects were checked,
- and the change is documented if it materially affects architecture or workflow.
