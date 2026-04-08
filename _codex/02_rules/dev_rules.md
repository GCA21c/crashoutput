# Development rules

## Data integrity
- Always prefer raw-source provenance.
- Never intentionally re-filter an already filtered channel.
- Validate whether a created helper channel is raw-based or derived-based.
- If a calculation can use filtered original channels directly, prefer that over creating extra channels.

## Scope control
- Change the smallest stable unit that solves the problem.
- Do not rename files, modules, or public UI labels unless the task requires it.
- Do not move documentation into `app/`.

## Naming and consistency
- Respect existing channel/result naming conventions.
- Keep UI labels, stored result keys, and generated-channel names aligned.
- When dummy names/labels are displayed, verify whether the UI expects user-entered names or fixed location codes.

## Multi-dummy discipline
- Treat ISO prefix grouping as a first-class routing key.
- Review B1~B6 rendering/state behavior when touching dummy-related UI.
- Confirm that injury modules use dummy factors loaded from dummy-set configuration where required.

## Shared-engine discipline
- Before editing one injury module, inspect `common_engines.py` and neighboring injury modules for coupling.
- Before editing UI pages, inspect component contracts in `app/ui/components/`.

## Environment-aware discipline
- Assume the editing environment and the final validation environment may differ.
- Prefer platform-safe behavior for file paths, text encoding, icon loading, and filesystem assumptions.
- Treat font availability and Tk / matplotlib rendering as cross-platform risks that may differ between macOS and Windows.
- Avoid documenting or committing sensitive environment details such as IP addresses, internal network names, or private access routes.
- When local testing is limited to the current host OS, call out likely Windows-specific validation risks clearly.

## Documentation discipline
For any material change, add a short log under `_codex/08_change_logs/` with:
- what changed,
- why,
- impacted files,
- regression risks,
- next checks.
