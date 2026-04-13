# Developed by GCA21c using CODEX-assisted workflow / gca21c@gmail.com
1. 이 프로그램은 자동차충돌시험 시 취득하는 데이터를 분석할 수있도록 가공하는 python 기반 프로그램 입니다.
4. 개발목표는 한국을 포함한 북미,유럽의 충돌안전성능 법규 및 상품성 시험을 기준으로 데이터를 가공하고 리포트 할 수 있어야 합니다.
5. 데이터 처리를 위해 SAE J211, ISO 6487의 규칙과 KMVSS, NHTSA-FMVSS, NCAP, IIHS등의 절차 및 기준을 따름니다.
6. 현재는 개발중이며 프로그램 스트럭쳐, 계산엔진 및 모듈을 50%가량 완성한 상태 입니다.
7. 프로그램의 가장 큰 이슈는 전문 프로그램 대비 부동소수점 정밀도, Sample indexing, Time-based sliding window정의 방식 차이로 인해 3ms 구간 적분/평균 계산에서 미세한 오차가 발생 할 수 있어 이를 극복하기 위해 연구중 입니다.
8. 완성이 되고 검증이 된다면 OPENSOURCE 배포를 검토중 입니다.
