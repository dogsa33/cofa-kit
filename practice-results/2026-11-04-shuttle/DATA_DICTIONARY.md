# 데이터 계약 및 기본 정책

모든 CSV는 `UTF-8 with BOM`, 첫 행은 헤더, 첫 열부터 순서 유지. 실제 프로젝트는 UTF-8 또는 UTF-8-BOM을 모두 처리해야 합니다. `datasets/<이름>/`은 **각각 완전한 스냅샷**입니다. 일부 파일만 수정하는 패치가 아닙니다. `datasets/base/` 기준 값은 시험 연습용 합성 자료입니다.

| 파일 | 유일키 | 필수 열·의미 |
| --- | --- | --- |
| `employees.csv` | employee_id | employee_id, name, home_x_km, home_y_km, site_id, active(0/1), suggested_stop_id(참고) |
| `sites.csv` | site_id | site_id, name, x_km, y_km |
| `stops.csv` | stop_id | stop_id, name, x_km, y_km, active(0/1), existing_route(0/1) |
| `nodes.csv` | node_id | node_id, x_km, y_km. DEPOT 및 전체 사업장·정류장 포함. **이 파일은 합성 시각화 좌표용** |
| `access_times.csv` | employee_id+stop_id | employee_id, stop_id, distance_km(>=0), walking_minutes(>=0). 구성원→정류장 접근시간; 직접거리 대체 금지 |
| `travel_times.csv` | from_node_id+to_node_id | from_node_id, to_node_id, minutes(양의 정수). **방향별** 전 노드 간 완전 연결(`from != to`) |
| `vehicles.csv` | vehicle_id | vehicle_id, capacity(양의 정수), depot_node_id, active(0/1) |
| `shifts.csv` | shift_date+employee_id | shift_date(YYYY-MM-DD), employee_id, status(WORK/OFF/LEAVE/TRAINING), shift_code, start_time(HH:MM), end_time(HH:MM) |
| `calendar.csv` | date | date(YYYY-MM-DD), is_workday(0/1), label |
| `demo_accounts.csv` | username | username, role(ADMIN/EMPLOYEE), employee_id(ADMIN은 공란), initial_password, active(0/1). 테스트에만 사용하고 초기화 후 원문 저장 금지 |
| `constraints.json` | - | 승인된 모의 과제의 필수 제약 기본값; 운영자가 노선 목표를 선택/변경할 수 있음 |

## 날짜·시간

- 실제 타임존은 모든 일시를 `Asia/Seoul` (+09:00)로 해석합니다.
- `shift_date`는 **근무 시작일**. 종료 시간이 시작시간보다 같거나 이르면 **다음 날** 종료입니다 (예: 11/09 22:00~11/10 06:00).
- 근무일이면서 해당 일자 `WORK`인 활성 직원만 출근 1편 + 퇴근 1편 대상. `OFF/LEAVE/TRAINING`과 주말은 제외합니다.
- 출근: `shift_start - 40min <= arrival_at <= shift_start - 20min`; 퇴근: `shift_end + 10min <= departure_at <= shift_end + 30min`. 정확히 경계에 도착/출발한 경우 허용됩니다. 지나치게 이른 도착이나 늦은 퇴근 출발은 허용하지 않습니다.
- 출퇴근 차량은 해당 `site_id`만 서비스하고 복수 사업장 혼재 금지. 반대 방향 이동시간은 동일하다고 가정하지 않습니다.
- 정류장에서 승·하차가 있는 경우 해당 정류장 `departure_at - arrival_at >= 2min`(마지막 도착 종점은 정차시간을 요구하지 않음).
- 직원 도보 접근시간 `<= max_walk_minutes`, 실제 차량 승차시간 `<= max_ride_minutes`. 도보 좌표는 UI 렌더링용; **접근시간은 `access_times.csv`가 진실값**입니다.
- 버스 정원은 차량별 capacity 기준. 동일 버스 운행 간 중복 불가. 다음 운행 시작 전 **선행 운행 도착지→다음 출발지** 공차 이동시간과 10분 회차 시간을 확보. 첫 운행 전에 차량이 DEPOT에서 이동할 수 있다는 가정; 서비스 시작일 00:00부터 가용.
- 노선 방문 간 소요시간은 `travel_times.csv`에 있는 **그 방향의 직접 간선**을 사용. 버스가 특정 구간에서 이동하지 않은 시간을 별도 대기한 것으로 취급할 수는 있으나 이동시간을 실제보다 줄일 수 없음.
- 제공 좌표와 시간은 **실제 지역의 위치·도로·통행량을 의미하지 않음**.

## 기준 제약 및 남겨 둔 사용자 선택

`constraints.json`에는 필수 정책(최대 도보 18분, 최대 승차 95분, 정차 2분, 회차 10분, 출근 20~40분 전 도착, 퇴근 10~30분 후 출발)이 있습니다. **모두 모의 재현을 위한 숫자이며 공식 시험 기준이 아닙니다.** 차량 capacity와 active 값은 CSV 우선.

**미정 정책(반드시 사용자에게 선택받을 것):** 차량 대수·운행 횟수·총 운행시간·평균/최대 탑승시간의 우선순위/가중치를 어떻게 구성할 것인가? 최소한 두 대안과 추천 근거를 제시합니다. 불가능한 정책으로 전체 필수 제약을 무시하면 안 됩니다.

## 필수 적용 규칙

- 스냅샷 검증 실패 → **기존 유효 데이터, 버전, 마지막 성공 결과 변경 금지**.
- 입력 변경 성공 → **원자적 저장** + 증가한 dataset_version 기록 + 자동 계산. 정책 변경도 policy_version 증가 + 자동 계산.
- 구버전 결과는 명확히 STALE. `READY`는 현재 dataset_version / policy_version과 정확히 일치하고 계산 검증을 통과한 경우만.
- 정상 구조 데이터라도 정류장 폐쇄 등으로 현실적으로 해를 찾지 못할 수 있습니다. 이때 인원을 누락해 가짜 PASS를 만들지 말고 INFEASIBLE 상태와 사유를 사용자에게 표시합니다.
