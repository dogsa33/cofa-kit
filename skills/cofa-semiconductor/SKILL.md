---
name: cofa-semiconductor
description: 반도체 제조 데이터에서 조인·수율·SPC 원리를 정확히 해석하고 검증한다.
---

# 반도체 데이터분석 선택 지침

- 반도체/제조 과제일 때만 읽는다. `examples/joins/`, `examples/semiconductor/`는 **합성 예제**이며 실전 데이터가 아니다.
- 검사 단위(웨이퍼/로트/재검사), ID 구성과 시간순서를 먼저 확인한다. `lot_id`만으로 결합하면 같은 wafer ID 재사용과 1:N 행 증폭이 발생할 수 있다.
- **수율**은 `(sum passed / sum tested) * 100`, 단순 퍼센트 평균 금지. 키 중복·잘못된 집계·0분모를 확인한다. 합성 예제 TOOL-A는 100/102, 전체 108/112다.
- **SPC I-MR**은 같은 계열, 오름차순 시각, 충분한 고정 기준 구간으로 산출한다. 신호는 이탈 징후이지 불량 원인 입증이 아니다. 기준 구간에 미래 정보를 섞거나 무리하게 합치지 않는다.
- `scripts/data_tools.py`의 `join/yield/spc/profile`로 작은 입력을 재현하고 `examples/semiconductor/expected.json`과 대조한다. 실제 과제에서는 입력 구조와 기준을 재확인한다.
