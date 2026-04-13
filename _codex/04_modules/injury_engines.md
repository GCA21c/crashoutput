# Injury engines

## Main code paths
- `app/services/injury/head_injury.py`
- `app/services/injury/neck_injury.py`
- `app/services/injury/chest_injury.py`
- `app/services/injury/femur_injury.py`
- `app/services/injury/tibia_injury.py`
- `app/services/injury/iliac_injury.py`
- `app/services/injury/knee_injury.py`
- `app/services/injury/pelvis_injury.py`
- `app/services/injury/common_engines.py`

## Shared concerns
- peak/clip engine behavior
- `High-Resolution 3ms Search` changes only the `Multiple Peak 3ms_Clip` cumulative-search resolution mode
- dummy-factor usage
- filtered-channel selection
- generated channel naming
- result persistence and UI handoff
- rule-specific required CFC should be checked against `_codex/05_reference/required_cfc_matrix.md`

## Specific hot points
### Head
- verify resultant-channel generation path
- confirm filtered source selection for HIC / 3ms / related metrics

### Neck
- verify sign handling, lever-arm logic, and configured dummy factors
- review consistency with upper/lower neck assumptions and MOC/MTO-style calculations

### Chest
- verify VC / displacement / acceleration channel sourcing
- avoid hidden sign-correction logic unless explicitly intended

## Rule
Any change in one injury engine should trigger a quick scan of `common_engines.py` and any directly shared UI/result path.
