# HEAD graph tab update

## What changed
- Updated the HEAD injury graph tabs from `HIC15 / HIC36 / 3ms Clip` to `HEAD X/Y/Z / HEAD RESULTANT`.
- Kept HEAD graph rendering within the existing `injury_page.py` flow and reused the current filtered HEAD channel bundle.
- Moved HIC15 and HIC36 interval highlighting onto the single `HEAD RESULTANT` graph.
- Adjusted HIC15 / HIC36 highlight colors for clearer contrast and restored the one Peak 3ms_Clip dashed line on `HEAD RESULTANT`.
- Updated the HEAD RESULTANT title rule to use `INJURY - HEAD RESULTANT (...)` while keeping HEAD X/Y/Z on the existing HEAD title form.

## Why
- The requested UI now separates component-axis review from resultant review while keeping the existing HEAD calculation path intact.

## Impacted files
- `app/ui/pages/injury_page.py`

## Behavior impact
- `HEAD X/Y/Z` shows only filtered HEAD X, Y, Z.
- `HEAD RESULTANT` shows filtered HEAD X, Y, Z, and HEAD Resultant together.
- `HEAD RESULTANT` also shows distinct HIC15 / HIC36 highlight bands and the one Peak 3ms_Clip dashed reference line.
- Saved legacy HEAD graph keys such as `hic15`, `hic36`, and `clip3` reopen on `HEAD RESULTANT` for compatibility.

## Regression risks
- Low to moderate UI risk around saved graph-tab restoration for older HEAD results.
- No intended change to HIC15, HIC36, or 3ms calculation values.

## Next checks
- Confirm both tabs render correctly after calculating HEAD on Windows.
- Confirm legacy saved datasets reopen HEAD graphs on the resultant tab without UI errors.
