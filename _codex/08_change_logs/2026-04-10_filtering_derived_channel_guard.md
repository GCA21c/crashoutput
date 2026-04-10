## Summary
- Prevented injury-derived helper channels from being re-filtered inside `DATA FILTERING`.

## Changed Files
- `app/ui/pages/filtering_page.py`

## Reason
- Injury helper channels such as `NECK Fx/Fz CFC600` are generated during pending filtering for later injury calculations.
- Those derived channels were being added to the filtering channel list and could be selected again, allowing accidental double filtering.

## Behavior Impact
- Injury-derived channels are no longer shown in the selectable filtering list.
- If a derived injury channel still reaches the apply path, filtering is blocked and excluded from the request.
- `FILTERING!` commit behavior is unchanged; only the selectable/apply stage is guarded.

## Known Risks
- The guard is based on `derived_channels[*].purpose` ending with `_injury`.
- Non-injury derived channels remain filterable.

## Follow-up
- If needed, add a read-only derived-channel inspector so users can verify pending helper channels without exposing them to refiltering.
