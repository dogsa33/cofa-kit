# 참고 출처와 범위

- 원본 공개 준비 키트 및 분석 예제: https://github.com/ripplelover/cofa-ready-kit (MIT), 개인 Fork: https://github.com/dogsa33/cofa-ready-kit
- 통근버스 사전설계 참고: https://github.com/Hantastic-02/h-kit/blob/main/study/04_%ED%86%B5%EA%B7%BC%EB%B2%84%EC%8A%A4_%EC%82%AC%EC%A0%84%EC%84%A4%EA%B3%84.md — 비공식 연습 문서로, 실제 문제 원본이나 정답으로 검증된 것은 아님
- Human-in-the-loop 기록 방식 비교 참고: https://github.com/NaYoung1017/my-cofa-plugin — 일부 원칙만 독립적으로 구성. 원본 전체 설치기/서브에이전트는 포함하지 않음
- 직원 셔틀 최적화 코드 참고: https://github.com/Yohannes33/route-optimization-api — 링크만 제공. 본 합성 검증기는 OR-Tools를 사용하지 않음

기존 공개 예제의 `defects.csv`, `examples/joins/*`, `examples/semiconductor/*`의 입력과 expected JSON을 복제하여 유지했습니다. 통근버스 입력과 정답 예시는 별도 합성 데이터입니다. 상기 참고 문서를 실제 과제의 공식 조건으로 단정하지 않습니다.

본 패키지는 새로 정리한 **독립 간소화판**이며, 원본 Fork 전체의 실행 도구·MCP·117개 테스트·긴 연구 문서를 그대로 재배포한 완전 복제본은 아닙니다.
