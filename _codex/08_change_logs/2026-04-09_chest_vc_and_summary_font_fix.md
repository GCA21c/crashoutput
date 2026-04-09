# 2026-04-09 Chest VC And Summary Font Fix

## Changed Files
- `app/services/preprocessing/service.py`
- `app/ui/pages/filtering_page.py`
- `app/ui/pages/injury_page.py`
- `app/core/isocode/engine.py`

## Reason
- `NECK` 결과 요약 텍스트에서 시스템 기본 폰트와 다른 glyph fallback이 섞여 보였다.
- `CHEST` displacement의 `CFC600` 보조 채널이 filtering 단계에서 이미 처리된 working dataframe 기준으로 다시 만들어질 수 있었고, 저장 시 rename 이후에도 파생 채널의 `source_channel` 참조가 충분히 갱신되지 않았다.
- 그 결과 `VC SAE J1727`와 `VC ECE-R94`가 사실상 같은 displacement 경로를 타면서 그래프와 결과값이 과도하게 겹칠 수 있었다.

## Behavior Impact
- 결과 요약 텍스트는 `TkDefaultFont` 기반으로 통일되어 기본 시스템 폰트로 렌더링된다.
- `CHEST disp -> CFC600` 파생 채널은 가능하면 `original_df`의 raw-aligned source에서 생성된다.
- ISO code rename 이후에도 파생 채널 metadata의 `source_channel` 및 `filter_history.from_channel` 참조가 현재 컬럼명과 일치하도록 유지된다.
- chest 계산 직전 displacement filter label 판정은 단순 `channel_filter_labels` 대신 통합 channel metadata 기준으로 읽는다.
- chest 계산의 raw alignment / prefiltered lookup은 `root_source_channel`과 raw isocode를 사용해 원본 raw 채널을 더 정확히 찾는다.

## Known Risks
- 실제 수치 차이는 대표 CHEST 데이터셋으로 `VC SAE/ECE` before/after 비교가 아직 필요하다.
- 원본 채널명이 ISO code rewrite 규칙과 다르게 커스텀된 데이터셋에서는 raw source 복원이 제한될 수 있다.

## Follow-up
- 실제 CHEST 케이스 1~2건으로 `displacement CFC180`, `displacement CFC600`, `vc_ece`, `vc_sae`를 비교 검증한다.
- 필요하면 filtering 단계에서 `created_from_raw=False`인 chest VC 보조 채널에 대한 경고를 추가한다.
