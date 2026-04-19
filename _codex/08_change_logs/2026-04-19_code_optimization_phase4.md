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
- Fixed Phase 4-D input resolver pandas `Index` handling after user calculation test.
- Closed Phase 4-A/B/C/D after user testing passed.
- Implemented Phase 4-E REPORT SUMMARY Excel export route:
  - added `export_summary_report()` service entry point
  - changed `report_summary_page.py` to call the report service instead of the Excel writer directly
  - kept UI error handling, status update, completion dialog, and file open behavior in the page
- Closed Phase 4-E after user testing passed.
- Implemented Phase 4-F DATA FILTERING apply helper split:
  - added `app/services/filtering/application.py`
  - moved channel/filter map normalization into `normalize_channel_filter_map()`
  - moved filter application info text and AUTO SET detail text helpers out of the page
  - kept pending dataframe mutation and filtering engine invocation in `filtering_page.py`
- Implemented Phase 4-G DATA FILTERING commit helper split:
  - moved metadata key rename helper into `rename_metadata_keys()`
  - moved derived-channel reference rename helper into `rename_derived_channel_references()`
  - moved filtering history summary text into `filtering_summary_text()`
  - kept `save_filters()` and `workbench.apply_processed_dataframe()` in the page
- Closed Phase 4-F/G after user testing passed.
- Implemented Phase 4-H DATA FILTERING commit payload helper split:
  - moved commit metadata/history payload assembly into `build_filter_commit_payload()`
  - kept `save_filters()` validation, `_F` commit, refresh, and completion dialog in the page
- Fixed DATA OFFSET preview overlay state:
  - stored the pre-offset preview dataframe under `offset_preview_before_df` when committing `_O`
  - restored that preview dataframe when reopening `_O` files
  - stopped forcing the preview channel back to the first channel on every OFFSET page show

## Why
- Phase 4 targets orchestration code that was still inside UI pages and shell.
- The first Phase 4 batch keeps behavior boundaries stable while reducing duplicated metadata and report assembly logic.

## Risk
- Report payload key compatibility must remain unchanged.
- AUTO SET matching can affect which channels are preset, so the page wrapper must be tested with representative TEST SETUP data.
- Persistence metadata assembly affects saved pickle contents, so Save / `_R` reload / processed-stage save paths need user testing.
- Injury input resolver changes are intentionally limited to derived-channel lookup; raw alignment and on-demand CFC preparation remain in the page.
- Phase 4-E is a call-route change only and does not change Excel template mapping or workbook writing.
- Phase 4-F is an apply-map/status helper split only and does not change filtering math or commit behavior.
- Phase 4-G is a pure helper split for commit metadata renaming and does not change `FILTERING!` commit behavior.
- Phase 4-H is a payload assembly split only and does not change `FILTERING!` commit behavior.
- DATA OFFSET preview persistence is UI-only and does not change offset calculation or `pre_filter_reference_df`.
- Phase 4 intentionally stops before moving `save_filters()` itself, `_resolve_standard_series_for_calc()`,
  `_collect_chest_disp_prefiltered()`, or shell state lifecycle because those need stronger regression fixtures.
- Filtering math, injury calculation, derived channel generation, report extraction keys, saved metadata key names, and pickle format names were not changed.
