# File to responsibility map

## Entry / shell
| Path | Responsibility |
|---|---|
| `main.py` | launch entry point |
| `app/shell.py` | shell / composition |

## Core
| Path | Responsibility |
|---|---|
| `app/core/io/dataset_store.py` | dataset/state storage boundary |
| `app/core/isocode/engine.py` | ISO interpretation / grouping |
| `app/core/dummy/engine.py` | dummy profile coordination |
| `app/core/utils/formatting.py` | formatting helpers |

## Services
| Path | Responsibility |
|---|---|
| `app/services/io/csv_loader.py` | CSV ingest |
| `app/services/io/dat_loader.py` | DAT ingest |
| `app/services/preprocessing/service.py` | filtering / preprocessing engine |
| `app/services/injury/common_engines.py` | shared injury helpers |
| `app/services/injury/*.py` | module-specific injury logic |

## UI pages
| Path | Responsibility |
|---|---|
| `app/ui/pages/viewer_page.py` | viewer page |
| `app/ui/pages/filtering_page.py` | filtering page |
| `app/ui/pages/test_setup_page.py` | test mode / dummy configuration page |
| `app/ui/pages/dummy_set_page.py` | compatibility import shim for old DummySetPage references |
| `app/ui/pages/injury_page.py` | injury workflow page |
| `app/ui/pages/report_summary_page.py` | summary report UI / save-restore table |
| `app/ui/pages/offset_page.py` | offset page |
| `app/ui/pages/trimming_page.py` | trimming page |

## Report
| Path | Responsibility |
|---|---|
| `app/report/mapping.py` | summary report snapshot / value extraction |
| `app/report/regulations/*.py` | regulation-specific report row order and labels |
| `_codex/04_modules/report.md` | report module maintenance workflow |

## UI components
| Path | Responsibility |
|---|---|
| `app/ui/components/workbench_viewer.py` | graph / workbench viewer |
| `app/ui/components/multi_dummy_panel.py` | multi-dummy UI block |
| `app/ui/components/scrollable_frame.py` | reusable scroll container |
