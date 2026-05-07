# System Map

## Runtime Structure
- `main.py`: startup splash, Tk root, app launch
- `app/shell.py`: top-level shell, navigation, shared state
- `app/ui/pages/`: workflow pages
- `app/ui/components/`: reusable UI widgets
- `app/services/io/`: DAT/CSV loading
- `app/services/preprocessing/`: offset/filtering/trimming support
- `app/services/injury/`: injury calculation engines
- `app/services/state/`: injury payload/registry helpers
- `app/core/`: ISO parsing, dummy profiles, dataset store, common domain utilities
- `app/report/`: summary, plotting, formatter, Excel/PPT export

## Data Flow
1. Loader reads DAT/CSV into dataframe + metadata.
2. ISO/dummy metadata routes B1~B6 slots.
3. Preprocessing produces working data while preserving raw reference policy.
4. Injury modules calculate metrics/graphs.
5. Results enter payload/registry store.
6. Report Summary, Plotting, Excel/PPT export read payload through common accessors/formatters.

## Key Contracts
- ISO prefix B1~B6 is the first routing key.
- TEST SETUP dummy config must match filtering/injury/report routing.
- `metadata["injury_saved_results"]` is the canonical result owner.
- graph title/text/layout belongs to formatter/policy layer, not calculation layer.
- Video Analysis is independent from injury/report calculation state except for loaded dataset channels.

## Broad Review Files
Touch these carefully; inspect adjacent callers before edits.
- `app/services/preprocessing/service.py`
- `app/services/injury/common_engines.py`
- `app/ui/pages/injury_page.py`
- `app/services/state/injury_result_store.py`
- `app/services/state/injury_metric_canonical.py`
- `app/report/engine.py`
- `app/report/plotting_service.py`
- `app/report/formatters/`
- `app/core/dummy/engine.py`
- `app/core/isocode/engine.py`

## Future Extension Path
- Add test-mode/dummy-specific criteria in `app/core/dummy/` and `app/services/injury/`.
- Store new calculation outputs in payload/registry first.
- Then expose them through Report Summary, Plotting formatter, and export templates.
