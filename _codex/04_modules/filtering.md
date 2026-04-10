# Filtering / preprocessing

## Main code paths
- `app/services/preprocessing/service.py`
- `app/ui/pages/filtering_page.py`

## Responsibilities
- apply selected filtering pipeline
- create only the necessary filtered outputs
- preserve raw-channel lineage for downstream calculations

## Critical rules
- raw -> filter must remain traceable
- do not stack filters unintentionally
- in this workflow, filtering/injury "raw reference" means the pre-filter reference dataset:
  offset has already been applied, but filtering/trimming has not
- verify whether helper channels for VC / neck / head use raw-based input paths
- changes here can affect every injury module
- confirm target CFC by criterion/rule using `_codex/05_reference/required_cfc_matrix.md`

## Review checklist
- Are channel selection rules still correct?
- Can an existing filtered channel accidentally be used as new raw input?
- If target CFC is missing, does the rebuild path use `pre_filter_reference_df` instead of the first-loaded DAT raw?
- Are generated channels named consistently?
- Do downstream injury modules consume the intended filtered channels?
