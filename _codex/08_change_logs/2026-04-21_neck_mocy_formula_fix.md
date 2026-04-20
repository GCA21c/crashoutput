# 2026-04-21 neck MOCy formula fix

- file: `app/services/injury/neck_metrics.py`
- change: neck Nij/MOCy correction formula updated from `My + Fx * D` to `My - Fx * D`
- scope: MOCy-derived neck metrics and Nij case/value calculation
- unchanged:
  - UI sign option behavior
  - RS/FS display logic
  - neck peak force/moment presentation flow
