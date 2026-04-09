# Codex workflow

## Recommended operating sequence
1. Open repository root.
2. Read root `AGENTS.md`.
3. Confirm the `crash-reference` MCP server is available when external crash-document lookup is needed.
4. Read module docs relevant to the request.
5. Inspect the exact code files to be changed.
6. Treat user wording like `소스자료` as the same external reference flow through `crash-reference`.
7. Use `crash-reference` for source lookup before changing crash criteria, filtering, or rating logic.
8. Apply minimal code changes.
9. Re-check adjacent modules for side effects.
10. Record a concise change log if the change is material.

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
