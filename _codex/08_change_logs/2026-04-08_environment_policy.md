# Environment policy update

## What changed
- Added non-sensitive working environment assumptions to project documentation.
- Added environment-aware development rules for cross-platform work.
- Added workflow reminders for macOS development and Windows validation paths.

## Why
- The project is edited in one environment and manually validated in another.
- Capturing that expectation helps reduce platform-specific regressions and avoids storing sensitive network details in repository docs.

## Impacted files
- `_codex/00_project/project_overview.md`
- `_codex/02_rules/dev_rules.md`
- `_codex/03_workflows/codex_workflow.md`

## Behavior impact
- No runtime code behavior changed.
- Future development and review should explicitly consider macOS-to-Windows validation differences.

## Regression risks
- Low runtime risk because this is documentation-only.
- Moderate process risk if future contributors ignore the new environment notes.

## Next checks
- Apply the environment policy when reviewing UI, file IO, font, icon, and encoding changes.
- Keep future environment notes free from IP addresses and other sensitive network details.
