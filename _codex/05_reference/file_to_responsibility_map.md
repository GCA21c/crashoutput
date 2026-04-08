# File to responsibility map

## Entry and shell
- `main.py` -> launch entry point
- `app/shell.py` -> shell/composition

## Core
- `app/core/io/dataset_store.py` -> dataset/state storage boundary
- `app/core/isocode/engine.py` -> ISO interpretation/grouping
- `app/core/dummy/engine.py` -> dummy profile coordination
- `app/core/utils/formatting.py` -> formatting helpers

## Services
- `app/services/io/csv_loader.py` -> CSV ingest
- `app/services/io/dat_loader.py` -> DAT ingest
- `app/services/preprocessing/service.py` -> filtering/preprocessing engine
- `app/services/injury/common_engines.py` -> shared injury calculation helpers
- `app/services/injury/*.py` -> module-specific injury logic

## UI pages
- `app/ui/pages/viewer_page.py` -> viewer page
- `app/ui/pages/filtering_page.py` -> filtering controls/page
- `app/ui/pages/dummy_set_page.py` -> dummy configuration page
- `app/ui/pages/injury_page.py` -> injury workflow page
- `app/ui/pages/offset_page.py` -> offset-related page
- `app/ui/pages/trimming_page.py` -> trimming-related page

## UI components
- `app/ui/components/workbench_viewer.py` -> graph/workbench viewer
- `app/ui/components/multi_dummy_panel.py` -> multi-dummy UI block
- `app/ui/components/scrollable_frame.py` -> reusable scroll container
