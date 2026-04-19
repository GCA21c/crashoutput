# Code optimization Phase 4

## What changed
- Created branch `코드최적화p4`.
- Implemented Phase 4-A report orchestration split:
  - added `app/report/service.py`
  - moved SUMMARY REPORT payload row assembly and in-memory cache assembly behind service helpers
  - kept `report_summary_page.py` as the UI entry point
- Implemented Phase 4-B DATA FILTERING AUTO SET orchestration split:
  - added `app/services/filtering/presets.py`
  - moved preset measurement-family detection and AUTO SET channel map matching out of the page
  - kept pending dataframe application and `apply_filtering_with_derivatives()` unchanged
- Implemented Phase 4-C shell persistence orchestration split:
  - added `app/services/state/persistence.py`
  - moved repeated saved metadata assembly into `build_dataset_snapshot_metadata()`
  - kept save path selection, pickle writing, ISO metadata enrichment, and workbench state updates in `shell.py`
- Implemented Phase 4-D injury input lookup split:
  - added `app/services/injury/input_resolver.py`
  - moved derived-channel lookup into `find_derived_channel()`
  - kept `_resolve_standard_series_for_calc()` in `injury_page.py`

## Why
- Phase 4 targets orchestration code that was still inside UI pages and shell.
- The first Phase 4 batch keeps behavior boundaries stable while reducing duplicated metadata and report assembly logic.

## Risk
- Report payload key compatibility must remain unchanged.
- AUTO SET matching can affect which channels are preset, so the page wrapper must be tested with representative TEST SETUP data.
- Persistence metadata assembly affects saved pickle contents, so Save / `_R` reload / processed-stage save paths need user testing.
- Injury input resolver changes are intentionally limited to derived-channel lookup; raw alignment and on-demand CFC preparation remain in the page.
- Filtering math, injury calculation, derived channel generation, report extraction keys, saved metadata key names, and pickle format names were not changed.
