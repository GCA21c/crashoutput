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
| `app/services/filtering/presets.py` | DATA FILTERING AUTO SET preset matching orchestration |
| `app/services/preprocessing/service.py` | filtering / preprocessing engine |
| `app/services/injury/common_engines.py` | shared injury helpers |
| `app/services/injury/input_resolver.py` | injury input channel lookup helper |
| `app/services/injury/*.py` | module-specific injury logic |
| `app/services/state/persistence.py` | saved dataset metadata assembly helper |

## UI pages
| Path | Responsibility |
|---|---|
| `app/ui/styles.py` | shared Tk color/font constants |
| `app/ui/pages/viewer_page.py` | viewer page |
| `app/ui/pages/filtering_page.py` | filtering page |
| `app/ui/pages/test_setup_page.py` | test mode / dummy configuration page |
| `app/ui/pages/dummy_set_page.py` | compatibility import shim for old DummySetPage references |
| `app/ui/pages/injury_page.py` | injury workflow page |
| `app/ui/pages/report_summary_page.py` | summary report UI / save-restore table |
| `app/ui/pages/report_summary_constants.py` | summary report UI labels, table headings, and presentation status strings |
| `app/ui/pages/offset_page.py` | offset page |
| `app/ui/pages/trimming_page.py` | trimming page |

## Report
| Path | Responsibility |
|---|---|
| `app/report/engine.py` | summary report snapshot / value extraction |
| `app/report/occupants.py` | report occupant slot normalization and merge helpers |
| `app/report/service.py` | summary report payload/cache orchestration helpers |
| `app/report/registry.py` | report rule/template registry |
| `app/report/rules/*.py` | regulation-specific report row order and labels |
| `app/report/templates/*.py` | Excel template anchors, aliases, and export rules |
| `app/report/exporters/*.py` | report export writers |
| `app/report/exporters/runtime.py` | Excel export filename, output folder, and OS open helpers |
| `_codex/04_modules/report.md` | report module maintenance workflow |
| `_codex/05_reference/excel_export_mapping.md` | Excel export mapping reference |

## UI components
| Path | Responsibility |
|---|---|
| `app/ui/components/workbench_viewer.py` | graph / workbench viewer |
| `app/ui/components/multi_dummy_panel.py` | multi-dummy UI block |
| `app/ui/components/scrollable_frame.py` | reusable scroll container |
