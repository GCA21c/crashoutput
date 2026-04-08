# Project overview

## Project type
Desktop Python crash-analysis tool with UI-driven workflow.

## Current repository shape
This repository already uses the following production layout:
- `main.py` as app launcher
- `app/core/` for core data/domain utilities
- `app/services/` for IO, preprocessing, and injury logic
- `app/ui/` for pages, viewer orchestration, and UI components

## Working environment assumptions
- Day-to-day editing may happen from a macOS host through a remote IDE / SSH workflow.
- Final manual validation may happen after downloading the repository into a Windows environment.
- Repository documentation should not record sensitive network information such as IP addresses, hostnames, or internal routing details.
- Cross-platform behavior matters for UI, file paths, fonts, icon loading, encoding, and generated artifacts.

## Main goal
Build and maintain a DIAdem-like crash-analysis workflow with strong support for:
- filtering and preprocessing,
- multi-dummy handling,
- ISO-code based grouping,
- injury computations,
- and traceable UI-driven analysis.

## Core philosophy
1. Use raw source data wherever possible.
2. Avoid accidental re-filtering of already filtered channels.
3. Avoid excessive derived-channel proliferation.
4. Keep shared engines centralized.
5. Preserve consistency between UI state, dummy settings, and injury calculations.
