# 출력 데이터 계약 | `artifacts/route_plan.json`

웹앱은 실제 계산한 운행 결과를 JSON으로 내보내야 합니다. 아래는 **자료형을 설명하는 형식 예시**이며 완성된 노선/정답이 아닙니다.

```json
{
  "dataset_version": 1,
  "policy_version": 1,
  "dataset_fingerprint": "<64-character SHA-256 hex>",
  "generated_at": "2026-11-09T00:00:00+09:00",
  "status": "READY",
  "planning_dates": ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"],
  "trips": [
    {
      "trip_id": "T-EXAMPLE",
      "vehicle_id": "BUS01",
      "service_date": "2026-11-09",
      "direction": "INBOUND",
      "site_id": "SITE_A",
      "stops": [
        {"node_id": "ST01", "arrival_at": "2026-11-09T05:00:00+09:00", "departure_at": "2026-11-09T05:02:00+09:00"},
        {"node_id": "SITE_A", "arrival_at": "2026-11-09T05:30:00+09:00", "departure_at": "2026-11-09T05:30:00+09:00"}
      ],
      "passengers": [{"employee_id": "E001", "stop_id": "ST01"}]
    }
  ],
  "unserved": [],
  "metrics": {"unique_vehicles": 1, "trip_count": 1, "total_operating_minutes": 30, "average_ride_minutes": 28, "max_ride_minutes": 28, "unserved_count": 0},
  "policy": {"objective": "<user-approved-policy>", "priority_order": ["<first-objective>"]}
}
```

위 **T-EXAMPLE은 전체 근무자 배정이 없어 실제 READY 결과로 제출하면 안 되는 형식 설명**입니다. 실제 결과는 모든 근무일/구성원에 대해 생성해야 합니다.

## 필드의 의미

- `dataset_version`, `policy_version`: 적용·선택 시 증가하는 양의 정수. 실제 최신 버전과 일치해야 READY.
- `dataset_fingerprint`: 선택한 입력 파일들의 내용으로 계산한 SHA-256 지문. 기준/변경 케이스를 식별하기 위한 것.
- `generated_at`: 시간대가 포함된 실제 생성 시점. 과거 고정 텍스트를 재사용하면 안 됨.
- `status`: `READY | INFEASIBLE | ERROR`. 재계산 중 화면은 `CALCULATING`, 이전 계획은 `STALE`로 구분.
- `planning_dates`: 이번 최적화가 수행된 `YYYY-MM-DD` 근무일 배열.
- `trips`: 한 실제 운행을 표현. 각 편의 `trip_id`는 전체 결과에서 유일. 출근 `INBOUND`, 퇴근 `OUTBOUND`.
- `stops`: **실제 방문 순서대로** 정류장/사업장을 나열. 모든 시각은 ISO 8601 +09:00, `arrival_at <= departure_at`. `INBOUND`는 마지막 노드가 `site_id`, `OUTBOUND`는 첫 노드가 `site_id`.
- `passengers`: 해당 편에 탑승한 직원과 배정된 정류장. `INBOUND`에서 정류장에 승차해 사업장 도착, `OUTBOUND`에서 사업장 출발해 정류장 하차. 임의의 경유지와 혼동하지 말 것.
- `unserved`: 미배정 명단. 원소 예: `{ "service_date":"2026-11-10", "employee_id":"E007", "direction":"INBOUND", "reason":"NO_ACCESSIBLE_ACTIVE_STOP" }`. READY라면 빈 배열.
- `metrics`: 실제 trips/passengers에서 산출한 차량 고유 수, 총 운행 편수, 운행 분, 개인별 탑승시간 등. 화면 표시와 API 값이 일치해야 합니다.
- `policy`: 사용자에게 설명하고 승인받은 최적화 기준. 승인 없이 기본 정책을 선택한 것으로 표시하면 안 됨.

## 핵심 불변조건

1. 출퇴근 각각의 모든 대상 직원이 **정확히 한 번** 출현; 비대상자는 0번.
2. 모든 trips의 `vehicle_id`는 활성 차량. 인원 <= 실제 해당 차량 capacity.
3. 각 편의 직원 `site_id`는 편의 사업장과 같아야 함. 직원 정류장은 활성이고 도보 접근 제약 만족.
4. 모든 연속 노드 이동에는 방향별 간선이 존재하며 소요시간을 줄여 쓸 수 없음.
5. 정류장 정차·출퇴근 시각(출근 20~40분 전, 퇴근 10~30분 후)·최대 승차시간·동일 차량 재사용 간격을 모두 충족.
6. `INFEASIBLE/ERROR`이면 문제를 숨기지 않고 `unserved`/사유를 포함, READY인 척 할 수 없음.
7. 데이터나 정책 업데이트 후 출력 버전과 지문 및 실제 계산값이 해당 최신 입력과 일치해야 함.
