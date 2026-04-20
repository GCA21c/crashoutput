# Filtering module

이 문서는 filtering 동작의 개요만 다룬다.
RAW reference 정의와 baseline 규칙은 반드시 `raw_reference_policy.md`를 따른다.

## 역할
- CFC filtering 수행
- target class 적용
- 필요한 helper channel 생성 여부 판단
- TEST SETUP의 저장된 시험모드/더미 프로필/ISO slot 정보를 읽어 AUTO SET preset을 pending 상태에 적용

## 핵심 원칙
- 이미 필터링된 채널의 의도적 재필터링 금지
- target CFC가 없을 때 raw reference 기준으로만 재구축
- 원채널 직접 사용이 가능하면 파생 채널 최소화
- 모든 CFC filtering edge extension은 `End Points`로 고정한다.
  - 시작부 extension은 첫 sample 값을 반복한다.
  - 종료부 extension은 마지막 sample 값을 반복한다.
  - Zero Magnitude extension mode는 사용하지 않는다.
- AUTO SET은 확정 저장이 아니라 기존 `선택 채널에 적용`과 같은 pending preset helper로 유지한다.
- 최종 저장은 사용자가 `FILTERING!`을 눌렀을 때만 수행한다.

## CFC edge extension entry point
- 공통 CFC segment filtering entry point는 `app/services/preprocessing/service.py`의 `_apply_cfc_filter_segment()`이다.
- `_apply_cfc_filter_segment()`는 `_end_points_extend()`를 통해 padding 구간을 만든 뒤 기존 SAE J211 coefficient와 `filtfilt` 기반 phaseless filtering을 수행한다.
- manual DATA FILTERING, preprocessing-derived CFC channel, injury 계산 전 target CFC 재구축, neck injury용 CFC600/1000 준비 경로는 모두 이 entry point를 공유해야 한다.
- CFC 수학, coefficient 산출, CFC class handling은 이 문서의 extension mode 규칙과 분리해서 관리한다.

## 점검 포인트
- 입력 채널 lineage가 명확한가
- helper channel이 raw-based인가
- naming convention이 유지되는가
- injury path와 preprocessing path가 같은 기준을 보는가
- AUTO SET preset DB가 더미 프로필별 record를 분리해서 참조하는가

## DATA FILTERING channel display prefix
DATA FILTERING channel list rows may show a display-only prefix:

```text
002:B1:Head Acceleration X   [B1HEADCG00HFACXP]   [Raw]
```

Rules:
- `002:B1:` is only a UI label prefix.
- It must never be written into dataframe column names, filter-label keys, ISO rewrite keys,
  descriptions, units, derived-channel keys, report payloads, or saved injury data.
- DAT files store the display number in `metadata["dat_channel_index_map"]` at load time using
  DAT header block order. Time is `001`; data channels follow the DAT header order.
- `metadata["dat_channel_file_map"]` and `metadata["dat_channel_file_index_map"]` keep CHN file
  information for reference only. CHN file numbers are not used as the primary display number
  because some voltage/current channels can share the same `Ch###` prefix.
- If a channel is calculated/derived and has no DAT index, the display number uses `CALC`.
  Existing saved files without DAT index metadata can fall back to current dataframe order for
  display only.
