# ISO code and dummy profile routing

## Main code paths
- `app/core/isocode/constants.py`
- `app/core/isocode/models.py`
- `app/core/isocode/engine.py`
- `app/core/dummy/engine.py`
- `app/core/dummy/*_dummy_profiles.py`

## Responsibilities
- parse and interpret channel metadata / ISO patterns
- group channels by dummy position such as B1~B6
- map selected dummy type/profile to factors used by calculation modules

## Review checklist
- Does ISO grouping still detect the right dummy buckets?
- Do profile lookups still match the selected dummy type?
- Are fallback behaviors safe when metadata is missing?
- Are UI labels and internal routing keys still synchronized?
