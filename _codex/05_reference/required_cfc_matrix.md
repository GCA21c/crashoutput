# Required CFC Matrix

## Purpose
- Summarize `test mode / regulation -> required input CFC` rules using the structure and wording of `Crash Analysis Criteria 2.4.3`.
- Use this document before changing calculation-time validation, warning prompts, or auto-refilter behavior.
- Treat this as the working matrix for `head`, `neck`, `chest`, and `femur` where source material was confirmed.

## Source priority
1. `CrashAnalysisCriteria_2.4.3`
2. `SAE J211-1 2014-03`
3. `SafetyCompanion-2024`

## Head
### HIC / HIC15 / HIC36
- Main heading
  - `Chapter 2 Description of the Head Criteria`
- Subheading
  - `HIC`
- Required CFC
  - Default: `Head Acceleration X/Y/Z -> CFC 1000`
  - Exception: `UN-R80 -> CFC 600`
- Content note
  - HIC uses resultant head CG acceleration.
- Related regulations
  - `FMVSS 208`
  - `Euro NCAP, Frontal Impact`
  - `Euro NCAP, Side Impact`
  - `Euro NCAP, Pole Side Impact`
  - `UN-R80`
  - `ADR69/00`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.10-11

## Neck
### NIC (Frontal Impact UN)
- Main heading
  - `Chapter 3 Description of the Neck Criteria`
- Subheading
  - `NIC (frontal impact UN)`
- Required CFC
  - `Upper Neck Force X -> CFC 1000`
  - `Upper Neck Force Z -> CFC 1000`
- Related regulations
  - `Directive 96/79/EG`
  - `UN-R94`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.30-32

### NIC (Frontal Impact Euro NCAP)
- Main heading
  - `Chapter 3 Description of the Neck Criteria`
- Subheading
  - `NIC (Frontal Impact Euro NCAP)`
- Required CFC
  - `Upper Neck Force X -> CFC 1000`
  - `Upper Neck Force Z -> CFC 1000`
- Related regulations
  - `Euro NCAP, Frontal Impact`
  - `Euro NCAP, Assessment Protocol and Biomechanical Limits`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.33

### NIC (Frontal Impact FMVSS)
- Main heading
  - `Chapter 3 Description of the Neck Criteria`
- Subheading
  - `NIC (Frontal Impact FMVSS)`
- Required CFC
  - `Upper Neck Force Z -> CFC 600`
  - `Upper Neck Moment Y -> CFC 600`
- Related regulations
  - `FMVSS 208`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.34-36

### NIC (IIHS)
- Main heading
  - `Chapter 3 Description of the Neck Criteria`
- Subheading
  - `NIC (IIHS)`
- Required CFC
  - `Upper Neck Force Z -> CFC 1000`
  - `Upper Neck Force X -> CFC 1000`
- Related regulations
  - `IIHS, Frontal Offset Crashworthiness Evaluation`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.37

### Nij
- Main heading
  - `Chapter 3 Description of the Neck Criteria`
- Subheading
  - `NIJ`
- Required CFC
  - `Upper Neck Force Z -> CFC 600`
  - `Upper Neck Moment Y / MOCy -> CFC 600`
- Content note
  - `Total Moment` must be calculated in accordance with `MOC`.
  - Case selection is sign-dependent and uses AND logic.
- Related regulations
  - Covered in the criterion chapter and used across frontal dummy criteria tables.
- Source
  - `Crash Analysis Criteria 2.4.3`, p.38-39

## Chest
### VC
- Main heading
  - `Chapter 4 Description of the Chest Criteria`
- Subheading
  - `VC`
- Required CFC
  - `UN-R94 / UN-R95 / Euro NCAP -> Chest or rib deflection path CFC 180`
  - `SAE J1727 frontal impact -> Chest deflection path CFC 600`
- Content note
  - VC is deformation-based, not direct chest acceleration multiplication.
  - `Only the crush is included in the calculation.`
- Related regulations
  - `UN-R94`
  - `UN-R95`
  - `Euro NCAP, Frontal Impact`
  - `Euro NCAP, Side Impact`
  - `SAE J1727`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.52-54

### TTI(d)
- Main heading
  - `Chapter 4 Description of the Chest Criteria`
- Subheading
  - `TTI(d)`
- Required CFC
  - preprocess acceleration sensors with `CFC 180`
  - then follow the extra TTI preprocessing sequence described in the chapter
- Content note
  - Uses upper/lower rib acceleration and lower spine acceleration.
  - This is side-impact oriented (`USSID`, `SIDH3`).
- Related regulations
  - `FMVSS 214`
  - `SAE J1727`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.56-57

### ThAC
- Main heading
  - `Chapter 4 Description of the Chest Criteria`
- Subheading
  - `ThAC`
- Required CFC
  - `Chest Acceleration X/Y/Z -> CFC 180`
- Content note
  - Xms-type acceleration criterion.
  - This is a chest acceleration criterion, not VC.
- Related regulations
  - `UN-R80`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.58

### CTI
- Main heading
  - `Chapter 4 Description of the Chest Criteria`
- Subheading
  - `CTI`
- Required CFC
  - `Chest Acceleration X/Y/Z -> CFC 180`
  - `Chest Displacement X -> CFC 600`
- Content note
  - CTI is the 3 ms value of resultant spinal acceleration plus chest deflection.
  - This is frontal-impact oriented in the chapter text.
- Related regulations
  - `FMVSS 208 proposal (September 1998)`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.59-60

## Femur
### FFC (UN)
- Main heading
  - `Chapter 5 - Description of Criteria for the Lower Extremities`
- Subheading
  - `FFC (UN)`
- Required CFC
  - `Femur Force Z -> CFC 600`
- Related regulations
  - `UN-R94`
  - `Directive 96/79/EG`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.70-71

### FFC (Euro NCAP)
- Main heading
  - `Chapter 5 - Description of Criteria for the Lower Extremities`
- Subheading
  - `FFC (Euro NCAP)`
- Required CFC
  - `Femur Force Z -> CFC 600`
- Related regulations
  - `Euro NCAP, Frontal Impact Testing Protocol`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.72-73

### FFC (IIHS)
- Main heading
  - `Chapter 5 - Description of Criteria for the Lower Extremities`
- Subheading
  - `FFC (IIHS)`
- Required CFC
  - `Femur Force Z -> CFC 600`
- Related regulations
  - `IIHS`
- Source
  - `Crash Analysis Criteria 2.4.3`, p.73-74

## Cross-check with SAE J211-1
- `Head accelerations (linear and angular) -> CFC 1000`
- `Neck forces -> CFC 1000`
- `Neck moments -> CFC 600`
- `Thorax spine accelerations -> CFC 180`
- `Rib accelerations -> CFC 1000`
- `Sternum accelerations -> CFC 1000`
- `Deflections -> CFC 600`
- `Displacements -> CFC 180`
- `Femur/Knee/Tibia/Ankle forces -> CFC 600`
- Source
  - `SAE J211-1 2014-03`, p.8

## Implementation guidance
- Do not warn at channel-selection time only from a generic preferred CFC.
- First resolve the intended criterion or regulation.
- Then compare the effective resolved input channel against the required CFC in this matrix.
- For mixed-mode modules such as chest:
  - treat `ACC`, `DISP`, `VC-ECE`, and `VC-SAE` as separate validation paths.
- If the required path is missing:
  - prefer warning during calculation,
  - show current filter state,
  - show required state,
  - show whether raw-based rebuilding is available.

## Open items
- Add pelvis, knee, tibia, and iliac when their source chapters are reviewed in the same way.
- Convert this matrix into machine-readable validation rules after UI warning flow is designed.
