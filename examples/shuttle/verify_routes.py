#!/usr/bin/env python3
"""Independent synthetic commuter-shuttle constraint checker (stdlib only).

It validates an already generated timetable, and NEVER claims route optimality.
Example data are synthetic and not official contest inputs/outputs.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

MAX_SEATS = 45
INBOUND_EARLY_MIN = 20
OUTBOUND_AFTER_MIN = 10


def load_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"{path.name}: 필수 컬럼 누락: {', '.join(sorted(required))}")
        rows = list(reader)
    if any(any(not (r.get(k) or "").strip() for k in required) for r in rows):
        raise ValueError(f"{path.name}: 필수 값 누락")
    return rows


def local_time(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("시각은 +09:00과 같은 오프셋을 포함해야 합니다")
    return value


def load_dataset(data_dir: Path) -> tuple[dict, dict, dict]:
    workers: dict[str, dict] = {}
    for row in load_csv(data_dir / "employees.csv", {"employee_id", "stop_id", "site_id"}):
        employee_id = row["employee_id"]
        if employee_id in workers:
            raise ValueError(f"employees.csv: 직원 ID 중복 {employee_id}")
        workers[employee_id] = row

    shifts: dict[tuple[str, str], dict] = {}
    for row in load_csv(data_dir / "shifts.csv", {"employee_id", "is_working", "start_at", "end_at"}):
        eid = row["employee_id"]
        if eid not in workers:
            raise ValueError(f"shifts.csv: 존재하지 않는 직원 ID {eid}")
        if row["is_working"] not in {"0", "1"}:
            raise ValueError(f"shifts.csv: 잘못된 근무 여부 {eid}")
        start, end = local_time(row["start_at"]), local_time(row["end_at"])
        if end <= start:
            raise ValueError(f"shifts.csv: 종료 시각이 시작보다 빠름 {eid}")
        key = (start.date().isoformat(), eid)
        if key in shifts:
            raise ValueError(f"shifts.csv: 직원별 근무일 중복 {key}")
        shifts[key] = {"work": row["is_working"] == "1", "start": start, "end": end}

    travel: dict[tuple[str, str], int] = {}
    for row in load_csv(data_dir / "travel_times.csv", {"from", "to", "minutes"}):
        key = (row["from"], row["to"])
        if key in travel:
            raise ValueError(f"travel_times.csv: 이동시간 키 중복 {key}")
        try:
            minutes = int(row["minutes"])
        except ValueError as exc:
            raise ValueError(f"travel_times.csv: 이동시간이 정수가 아님 {key}") from exc
        if minutes <= 0 or key[0] == key[1]:
            raise ValueError(f"travel_times.csv: 이동시간 또는 노드 범위 오류 {key}")
        travel[key] = minutes
    if not workers or not shifts or not travel:
        raise ValueError("직원·근무표·이동시간이 모두 1개 이상 필요")
    return workers, shifts, travel


def validate(workers: dict, shifts: dict, travel: dict, solution: dict) -> list[str]:
    """Return concrete violations for a proposed route solution."""
    errors: list[str] = []
    trips = solution.get("trips")
    if not isinstance(trips, list):
        return ["SCHEMA: trips 배열 누락"]
    seen_trip_ids = set()
    assigned: dict[tuple[str, str, str], int] = {}
    for pos, trip in enumerate(trips, 1):
        if not isinstance(trip, dict):
            errors.append(f"SCHEMA: {pos}번째 trip이 객체가 아님")
            continue
        name = str(trip.get("id", f"trip-{pos}"))
        if name in seen_trip_ids:
            errors.append(f"TRIP_DUP: {name}")
        seen_trip_ids.add(name)
        direction = trip.get("direction")
        service_date = trip.get("service_date", "")
        if direction not in {"inbound", "outbound"}:
            errors.append(f"SCHEMA: {name} 운행 방향 오류")
            continue
        try:
            datetime.strptime(service_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            errors.append(f"SCHEMA: {name} service_date 오류")
            continue
        passengers = trip.get("employee_ids")
        legs = trip.get("legs")
        capacity = trip.get("capacity")
        if not isinstance(passengers, list) or not isinstance(legs, list) or not legs:
            errors.append(f"SCHEMA: {name} 승객 또는 운행 구간 오류")
            continue
        if not isinstance(capacity, int) or isinstance(capacity, bool) or not 1 <= capacity <= MAX_SEATS:
            errors.append(f"CAPACITY: {name} 차량 정원은 1~{MAX_SEATS}석")
            continue
        if len(passengers) > capacity:
            errors.append(f"CAPACITY: {name} {len(passengers)}명 > {capacity}석")
        if len(passengers) != len(set(map(str, passengers))):
            errors.append(f"DUP_IN_TRIP: {name} 동일 직원 중복")
        try:
            segments: list[tuple[str, str, datetime, datetime]] = []
            for leg in legs:
                a, b = str(leg["from"]), str(leg["to"])
                dep, arr = local_time(leg["depart_at"]), local_time(leg["arrive_at"])
                segments.append((a, b, dep, arr))
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"SCHEMA: {name} 구간 오류 {exc}")
            continue
        for i, (a, b, dep, arr) in enumerate(segments):
            expected = travel.get((a, b))
            if expected is None:
                errors.append(f"TRAVEL_MISSING: {name} {a}->{b} 방향의 이동시간 없음")
            elif arr - dep != timedelta(minutes=expected):
                errors.append(f"TRAVEL_TIME: {name} {a}->{b} 실제 {arr-dep} != 기준 {expected}분")
            if i and (segments[i - 1][1] != a or segments[i - 1][3] > dep):
                errors.append(f"CONTINUITY: {name} 구간 연결 또는 시각 역전 {i}")
        start_node, end_node = segments[0][0], segments[-1][1]
        visited = [start_node] + [s[1] for s in segments]
        for eid in passengers:
            if not isinstance(eid, str) or eid not in workers:
                errors.append(f"UNKNOWN_EMPLOYEE: {name} {eid}")
                continue
            key = (service_date, eid)
            shift = shifts.get(key)
            if shift is None or not shift["work"]:
                errors.append(f"OFF_OR_UNKNOWN_SHIFT: {name} {eid} 휴무 또는 근무표 없음")
                continue
            count_key = (service_date, eid, direction)
            assigned[count_key] = assigned.get(count_key, 0) + 1
            if assigned[count_key] > 1:
                errors.append(f"DUP_ASSIGN: {service_date} {eid} {direction} 중복")
            w = workers[eid]
            site, stop = w["site_id"], w["stop_id"]
            if direction == "inbound":
                if end_node != site or stop not in visited[:-1]:
                    errors.append(f"STOP_SITE: {name} {eid} 출근 정류장·사업장 오류")
                if segments[-1][3] > shift["start"] - timedelta(minutes=INBOUND_EARLY_MIN):
                    errors.append(f"ARRIVAL_LATE: {name} {eid} 출근 도착 조건 위반")
            else:
                if start_node != site or stop not in visited[1:]:
                    errors.append(f"STOP_SITE: {name} {eid} 퇴근 정류장·사업장 오류")
                if segments[0][2] < shift["end"] + timedelta(minutes=OUTBOUND_AFTER_MIN):
                    errors.append(f"DEPART_EARLY: {name} {eid} 퇴근 출발 조건 위반")
    for (date, eid), shift in shifts.items():
        if not shift["work"]:
            continue
        for direction in ("inbound", "outbound"):
            if assigned.get((date, eid, direction), 0) == 0:
                errors.append(f"MISSING_ASSIGN: {date} {eid} {direction}")
    return errors


def run(args: argparse.Namespace) -> int:
    workers, shifts, travel = load_dataset(Path(args.data_dir))
    with Path(args.routes).open(encoding="utf-8") as f:
        solution = json.load(f)
    errors = validate(workers, shifts, travel, solution)
    for error in errors:
        print("FAIL", error)
    if errors:
        print(f"검증 실패: {len(errors)}건. 최적성은 별도로 판단해야 합니다.")
        return 1
    print(f"PASS: 노선 {len(solution['trips'])}개 / 근무자 배정·정원·시각·방향별 이동시간 검사 통과. 최적성 검증은 하지 않음.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic shuttle route independent constraint verifier")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--routes", required=True)
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("INPUT_ERROR", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
