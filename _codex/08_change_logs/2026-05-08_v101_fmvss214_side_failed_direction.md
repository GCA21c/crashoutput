# 2026-05-08 v101 FMVSS214 SIDE Direction Failure

## Status
- Branch: `v101`
- Decision: discard this branch direction.
- Reason: the implementation direction did not preserve the existing INJURY UI/module workflow.

## What Went Wrong
- A new integrated `SIDE IMPACT` page was introduced too early.
- The new page did not follow the established `InjuryPage` layout, dummy tab behavior, graph tab behavior, result-summary style, and payload save/reload expectations.
- `SideImpactPage.apply_shared_dummy_config()` was implemented with a different method signature from existing injury pages, which broke `TEST SETUP -> set_shared_dummy_config()` propagation.
- The work assumed a unified side-impact page could replace/collect side injury behavior before confirming the desired module split with the user.

## User Intent Clarified
- FRONTAL should be used as the UI/workflow reference.
- Existing INJURY UI style must be preserved.
- HEAD can likely reuse the existing HEAD module when the calculation is equivalent.
- Other side body regions may need new modules because the physical quantities and criteria differ from frontal modules.
- If a design decision is unclear, ask before implementing, especially for module/page structure.

## Lessons
- Do not add a new top-level or integrated injury page just because it is technically convenient.
- For new test modes, first map each criterion to an existing module or a new module proposal.
- Reuse an existing module only when the measured quantity and calculation logic truly match.
- Add a new module only after confirming UI label, graph tabs, result text format, payload keys, and report linkage.
- Keep the existing `InjuryPage` contract unless a deliberate refactor is explicitly approved.
- Before coding criteria, separate dummy/profile routing, channel auto-selection, calculation engine, graph tabs, summary report rows, plotting text, and export mapping.

## Future Restart Plan
1. Use `main` as the clean baseline.
2. Keep SIDE profile/criteria research separate from code changes until the module map is confirmed.
3. Propose a SIDE module map before implementation.
4. Implement one vertical slice only after approval: auto channel selection, calculation, graph tabs, payload/registry, SUMMARY REPORT, and PLOTTING.

## Candidate Module Map For Later Review
- HEAD: reuse existing HEAD if HIC/resultant behavior is compatible.
- ES-2re chest/rib deflection: likely new side chest/rib module.
- ES-2re abdomen force: likely new side abdomen module.
- ES-2re pubic symphysis / pelvis force: likely new side pelvis module.
- SID-IIs lower spine acceleration / pelvis force: likely new SID-IIs side module or side pelvis/spine modules.

## Preserve From Investigation
- MCP references found:
  - `SafetyCompanion-2024` pages 94-95 for FMVSS214 side pole/MDB overview and criteria.
  - `CrashAnalysisCriteria_2.4.3` pages 62-65 for side rib/chest signal references.
- Sample DAT categories available in MCP:
  - `ES2re - SIDE POLE`
  - `SIDII2s - SIDE POLE`
  - `WSID - SIDE POLE`

## Do Not Carry Forward Blindly
- Do not reuse the abandoned integrated `SIDE IMPACT` page design.
- Do not assume ES-2 and ES-2re or SID-IIs Level C and Level D are interchangeable without criteria/factor confirmation.
- Do not wire FMVSS214 report rows to placeholder payload sections that are not produced by an approved injury module.
