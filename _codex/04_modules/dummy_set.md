# Dummy Set module

## Main code paths
- `app/ui/pages/dummy_set_page.py`
- `app/ui/components/multi_dummy_panel.py`
- `app/core/dummy/engine.py`
- `app/core/dummy/*.py` profile modules

## Responsibilities
- configure dummy count and dummy-specific metadata
- bind detected positions / ISO-grouped channels to dummy slots
- expose dummy factors/profile information used by injury calculations
- drive per-dummy labeling shown elsewhere in the UI

## Review checklist when changing this area
- Does dummy count update the visible input controls correctly?
- Does location detection still bind correctly?
- Do injury tabs/pages show the intended user names vs fixed position labels?
- Are dummy-factor-dependent calculations still reading the configured dummy data?
- Does state persist when moving between pages/modules?
