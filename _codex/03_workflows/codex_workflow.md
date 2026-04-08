# Codex workflow

## Recommended operating sequence
1. Open repository root.
2. Read root `AGENTS.md`.
3. Read module docs relevant to the request.
4. Inspect the exact code files to be changed.
5. Apply minimal code changes.
6. Re-check adjacent modules for side effects.
7. Record a concise change log if the change is material.

## For bug fixes
- reproduce mentally from page -> service -> core boundary
- identify state owner
- identify computation owner
- inspect shared helpers before patching

## For feature changes
- define whether the change is UI-only, service-only, or cross-layer
- preserve existing data flow unless change explicitly requires redesign
- update docs if architecture, workflow, or module contract changed

## Environment checks
- Keep in mind that development may happen on macOS while final manual verification may happen on Windows.
- Before closing a task that touches UI or file IO, quickly review path handling, font assumptions, icon behavior, encoding, and generated file expectations.
- Record environment-related risks in change logs without including sensitive network or machine-identifying details.
