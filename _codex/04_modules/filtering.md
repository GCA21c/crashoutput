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
- verify whether helper channels for VC / neck / head use raw-based input paths
- changes here can affect every injury module

## Review checklist
- Are channel selection rules still correct?
- Can an existing filtered channel accidentally be used as new raw input?
- Are generated channels named consistently?
- Do downstream injury modules consume the intended filtered channels?
