# 2026-04-22 docs current state refresh

## What
- updated `AGENTS.md` to point future sessions at current-state and payload-role docs
- added `_codex/03_workflows/current_program_state.md`
- added `_codex/04_modules/report_plotting.md`
- refreshed architecture/workflow/module docs to reflect:
  - canonical payload store direction
  - formatter/report/plotting current status
  - next planned work: sample-data collection and DAT-based automation

## Why
- the codebase moved beyond the old Phase 5-only optimization context
- future Codex sessions need one short document that explains the current branch baseline,
  canonical payload direction, formatter coverage, and the immediate next schedule

## Where
- `AGENTS.md`
- `_codex/01_architecture/system_map.md`
- `_codex/03_workflows/current_program_state.md`
- `_codex/03_workflows/refactor_phase_tracker.md`
- `_codex/03_workflows/refactor_master_plan.md`
- `_codex/04_modules/injury_ui.md`
- `_codex/04_modules/report_plotting.md`
- `_codex/05_reference/file_to_responsibility_map.md`

## Risk
- document-only change
- future sessions may still need code inspection for exact runtime behavior, but the current
  state and next direction should now be discoverable without reconstructing the recent history
