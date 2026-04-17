# 2026-04-17 TEST SETUP and filtering AUTO SET

- 무엇을: `DUMMY SET` UI를 `TEST SETUP`으로 명칭 변경하고 PRE-PROCESSING 첫 단계로 이동했다. 기존 `dummyset` page key와 `DummySetPage` import는 compatibility alias로 유지했다.
- 무엇을: `DATA FILTERING`에 `AUTO SET` 버튼을 추가하고, TEST SETUP의 `shared_dummy_config`와 ISO metadata를 읽어 channel별 CFC preset을 pending 상태에 일괄 적용하도록 했다.
- 무엇을: `app/core/dummy/filter_presets.py`에 FRONTAL / H3_50%M 및 FRONTAL / H3_5%F filtering preset record를 분리해 추가했다.
- 왜: 향후 TEST SETUP 기반 filtering preset 확장을 위해 UI 위치/명칭과 preset lookup 구조를 정리하기 위해서다.
- 어디를: `app/shell.py`, `app/ui/pages/test_setup_page.py`, `app/ui/pages/dummy_set_page.py`, `app/ui/pages/filtering_page.py`, `app/core/dummy/filter_presets.py`, `_codex/04_modules/*`, `_codex/05_reference/file_to_responsibility_map.md`
- 리스크: AUTO SET 매칭은 현재 ISO metadata의 dummy slot / sensor location / data type 해석 품질에 의존한다. ISO parse가 부족한 legacy 채널은 제한적 fallback만 적용된다.
- 비변경: filtering 수학 처리, offset/trimming 계산, injury 계산식, dummy factor 계산식은 변경하지 않았다.
