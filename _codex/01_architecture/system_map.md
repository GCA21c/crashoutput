# System map

## Runtime structure
- `main.py`
  - process entry point
- `app/shell.py`
  - top-level application shell / composition layer
- `app/ui/`
  - user-facing workflow and pages
- `app/services/`
  - application services for loading, preprocessing, and injury calculations
- `app/core/`
  - reusable domain logic, dummy profiles, ISO parsing, dataset storage, utilities

## High-level data flow
1. Load data through `app/services/io/`
2. Persist / route datasets through `app/core/io/dataset_store.py`
3. Resolve ISO grouping and dummy context through `app/core/isocode/` and `app/core/dummy/`
4. Run preprocessing through `app/services/preprocessing/service.py`
5. Trigger injury computations through `app/services/injury/`
6. Display/coordinate results through `app/ui/pages/` and `app/ui/components/`

## Architectural hotspots
### Multi-dummy flow
- UI pages choose and render dummy-specific settings
- ISO prefixes like B1~B6 partition channels
- dummy profile modules in `app/core/dummy/` provide factor/geometry context

### Filtering flow
- preprocessing service is a critical boundary
- filtering mistakes can propagate into every injury result
- raw-source traceability matters more than convenience channel creation

### Injury flow
- injury page orchestrates UI state
- actual calculations are distributed across `app/services/injury/*.py`
- shared computation helpers live in `common_engines.py`

## Change-risk rule
Changes in these areas require broader review:
- `app/services/preprocessing/service.py`
- `app/services/injury/common_engines.py`
- `app/ui/pages/injury_page.py`
- `app/ui/pages/dummy_set_page.py`
- `app/core/dummy/engine.py`
- `app/core/isocode/engine.py`
