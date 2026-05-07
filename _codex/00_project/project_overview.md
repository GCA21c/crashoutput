# Project Overview

Crashoutput™ is a desktop Python crash data analysis system.

## Product Goal
- Load crash test data.
- Preserve raw data provenance.
- Apply preprocessing and injury calculations.
- Organize results by test mode, dummy, slot, injury section, graph, and metric.
- Generate report summaries and template-based exports.
- Support video/pulse review for post-processing.

## Current Development Phase
- The main workflow is already built.
- Future work focuses on adding and validating injury criteria by test mode and dummy.
- The application must support different evaluation purposes:
  - regulation/legal test
  - product performance test
  - NCAP/IIHS or other mode-specific evaluations

## Repository Layout
- `main.py`: app entry and startup splash
- `app/`: production code
- `resources/`: templates and runtime assets
- `_codex/`: Codex rules, state summaries, module notes, change logs

## Documentation Policy
- Default reading should stay short: AGENTS, dev rules, current state, and relevant module docs.
- `_codex/08_change_logs/` is historical detail storage; do not read all logs by default.
- Update current summaries when architecture direction changes.
