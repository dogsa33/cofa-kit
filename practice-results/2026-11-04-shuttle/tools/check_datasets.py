#!/usr/bin/env python3
"""Check INPUT contracts only; this tool does NOT solve routes, authenticate users, or test the web app."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path

SCHEMAS={
 'employees.csv':('employee_id','name','home_x_km','home_y_km','site_id','active','suggested_stop_id'),
 'sites.csv':('site_id','name','x_km','y_km'),
 'stops.csv':('stop_id','name','x_km','y_km','active','existing_route'),
 'nodes.csv':('node_id','x_km','y_km'),
 'access_times.csv':('employee_id','stop_id','distance_km','walking_minutes'),
 'travel_times.csv':('from_node_id','to_node_id','minutes'),
 'vehicles.csv':('vehicle_id','capacity','depot_node_id','active'),
 'shifts.csv':('shift_date','employee_id','status','shift_code','start_time','end_time'),
 'calendar.csv':('date','is_workday','label'),
 'demo_accounts.csv':('username','role','employee_id','initial_password','active'),
}
KEYS={
 'employees.csv':('employee_id',),'sites.csv':('site_id',),'stops.csv':('stop_id',),
 'nodes.csv':('node_id',),'access_times.csv':('employee_id','stop_id'),
 'travel_times.csv':('from_node_id','to_node_id'),'vehicles.csv':('vehicle_id',),
 'shifts.csv':('shift_date','employee_id'),'calendar.csv':('date',),
 'demo_accounts.csv':('username',),
}

class InputContractError(ValueError):pass

def check(root:Path)->list[str]:
    """Returns actionable errors. Input normalization errors must not mutate the snapshot."""
    root=Path(root)
    errors=[]; table={}
    if not root.is_dir():return [f'{root}: 폴더가 존재하지 않습니다']
    for filename,header in SCHEMAS.items():
        path=root/filename
        if not path.is_file():
            errors.append(f'{filename}: 필수 파일 누락');continue
        try:
            with path.open('r',encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                actual=reader.fieldnames or []
                if len(actual)!=len(set(actual)):
                    errors.append(f'{filename}: 중복 헤더')
                missing=[k for k in header if k not in actual]
                if missing:
                    errors.append(f'{filename}: 필수 열 누락 {missing}');continue
                if actual!=list(header):
                    errors.append(f'{filename}: 헤더 이름/순서 불일치 {actual}')
                rr=[];seen=set()
                for row_num,row in enumerate(reader,2):
                    if None in row or any(v is None for v in row.values()):
                        errors.append(f'{filename}:{row_num}: CSV 열 수 불일치');continue
                    key=tuple(row[k] for k in KEYS[filename]);
                    if key in seen:
                        errors.append(f'{filename}:{row_num}: 중복 키 {key}')
                    seen.add(key);rr.append((row_num,row))
                table[filename]=rr
        except (OSError,UnicodeError,csv.Error) as e:
            errors.append(f'{filename}: CSV 읽기 실패 {e}')
    for filename,required in SCHEMAS.items():
        if filename not in table:return errors
    try:
        cfg=json.loads((root/'constraints.json').read_text(encoding='utf-8'))
        for k in ('planning_dates','arrival_before_shift_minutes','departure_after_shift_minutes','stop_dwell_minutes','turnaround_minutes','max_walk_minutes','max_ride_minutes','max_arrival_before_shift_minutes','max_departure_after_shift_minutes'):
            if k not in cfg: errors.append(f'constraints.json: 필수 {k} 누락')
    except (OSError,ValueError) as e:
        errors.append(f'constraints.json: 읽기 실패 {e}');return errors

    for key in ('arrival_before_shift_minutes','max_arrival_before_shift_minutes','departure_after_shift_minutes','max_departure_after_shift_minutes'):
        if key not in cfg or not isinstance(cfg[key],int) or cfg[key]<0:
            errors.append(f'constraints.json: {key}는 0 이상 정수여야 합니다')
    if all(key in cfg and isinstance(cfg[key],int) for key in ('arrival_before_shift_minutes','max_arrival_before_shift_minutes')):
        if cfg['max_arrival_before_shift_minutes']<cfg['arrival_before_shift_minutes']:
            errors.append('constraints.json: 최대 조기도착 여유는 최소 조기도착 여유 이상이어야 함')
    if all(key in cfg and isinstance(cfg[key],int) for key in ('departure_after_shift_minutes','max_departure_after_shift_minutes')):
        if cfg['max_departure_after_shift_minutes']<cfg['departure_after_shift_minutes']:
            errors.append('constraints.json: 최대 퇴근 대기는 최소 퇴근 여유 이상이어야 함')

    def rows(n):return [x for _,x in table[n]]
    employees={r['employee_id']:r for r in rows('employees.csv')}
    sites={r['site_id']:r for r in rows('sites.csv')}
    stops={r['stop_id']:r for r in rows('stops.csv')}
    nodes={r['node_id']:r for r in rows('nodes.csv')}
    vehicles={r['vehicle_id']:r for r in rows('vehicles.csv')}
    calendars={r['date']:r for r in rows('calendar.csv')}
    def positive_float(filename,line,row,col,positive=False):
        try:
            n=float(row[col]);
            if not math.isfinite(n) or (n<=0 if positive else n<0):raise ValueError()
            return n
        except (ValueError,TypeError):
            errors.append(f'{filename}:{line}: {col} 유한한 {"양수" if positive else "0 이상의 수"} 필요');return None
    def flag(filename,line,row,col):
        if row[col] not in ('0','1'):errors.append(f'{filename}:{line}: {col}는 0/1')
    def date(filename,line,v,col):
        try:dt.date.fromisoformat(v)
        except ValueError:errors.append(f'{filename}:{line}: {col} 날짜 YYYY-MM-DD 오류 {v}')
    def hhmm(filename,line,v,col):
        try:
            if len(v)!=5 or v[2]!=':':raise ValueError()
            a,b=map(int,v.split(':'))
            if a>23 or b>59 or a<0 or b<0:raise ValueError()
        except ValueError:errors.append(f'{filename}:{line}: {col} 시각 HH:MM 오류 {v}')
    def has_key(filename,line,col,key,collection):
        if key not in collection:errors.append(f'{filename}:{line}: {col} 존재하지 않는 ID {key}')

    for line,r in table['employees.csv']:
        has_key('employees.csv',line,'site_id',r['site_id'],sites)
        has_key('employees.csv',line,'suggested_stop_id',r['suggested_stop_id'],stops)
        flag('employees.csv',line,r,'active')
        for col in ('home_x_km','home_y_km'):positive_float('employees.csv',line,r,col)
    for filename in ('stops.csv','sites.csv','nodes.csv'):
        for line,r in table[filename]:
            for col in ('x_km','y_km'):positive_float(filename,line,r,col)
            if filename=='stops.csv':
                for col in ('active','existing_route'):flag(filename,line,r,col)
    expected_nodes=set(stops)|set(sites)|{'DEPOT'}
    if set(nodes)!=expected_nodes:
        errors.append(f'nodes.csv: 노드 ID 집합 불일치; 누락 {sorted(expected_nodes-set(nodes))}, 초과 {sorted(set(nodes)-expected_nodes)}')
    for line,r in table['vehicles.csv']:
        flag('vehicles.csv',line,r,'active')
        has_key('vehicles.csv',line,'depot_node_id',r['depot_node_id'],nodes)
        positive_float('vehicles.csv',line,r,'capacity',True)
        if not r['capacity'].isdigit():errors.append(f'vehicles.csv:{line}: capacity 양의 정수 필요')
    for line,r in table['access_times.csv']:
        has_key('access_times.csv',line,'employee_id',r['employee_id'],employees)
        has_key('access_times.csv',line,'stop_id',r['stop_id'],stops)
        for col in ('distance_km','walking_minutes'):positive_float('access_times.csv',line,r,col)
    expected_access={(e,s) for e in employees for s in stops}
    actual_access={(r['employee_id'],r['stop_id']) for r in rows('access_times.csv')}
    if expected_access!=actual_access: errors.append(f'access_times.csv: 모든 직원×정류장 조합 필요; 누락 {len(expected_access-actual_access)}건')
    for line,r in table['travel_times.csv']:
        for col in ('from_node_id','to_node_id'):has_key('travel_times.csv',line,col,r[col],nodes)
        if r['from_node_id']==r['to_node_id']:errors.append(f'travel_times.csv:{line}: 자기자신 간선 금지')
        positive_float('travel_times.csv',line,r,'minutes',True)
        if not r['minutes'].isdigit():errors.append(f'travel_times.csv:{line}: minutes 양의 정수 필요')
    expected_travel={(a,b) for a in nodes for b in nodes if a!=b}
    actual_travel={(r['from_node_id'],r['to_node_id']) for r in rows('travel_times.csv')}
    if expected_travel!=actual_travel:
        errors.append(f'travel_times.csv: 방향 간선 누락 {len(expected_travel-actual_travel)}개, 초과 {len(actual_travel-expected_travel)}개; 예 {sorted(expected_travel-actual_travel)[:3]}')
    for line,r in table['calendar.csv']:
        date('calendar.csv',line,r['date'],'date');flag('calendar.csv',line,r,'is_workday')
    for line,r in table['shifts.csv']:
        date('shifts.csv',line,r['shift_date'],'shift_date')
        has_key('shifts.csv',line,'employee_id',r['employee_id'],employees)
        if r['shift_date'] not in calendars:errors.append(f'shifts.csv:{line}: calendar에 해당 날짜 없음')
        if r['status'] not in {'WORK','OFF','LEAVE','TRAINING'}: errors.append(f'shifts.csv:{line}: status 허용값 오류 {r["status"]}')
        hhmm('shifts.csv',line,r['start_time'],'start_time');hhmm('shifts.csv',line,r['end_time'],'end_time')
    expected_shifts={(d,e) for d in cfg.get('planning_dates',[]) for e in employees}
    actual_shifts={(r['shift_date'],r['employee_id']) for r in rows('shifts.csv')}
    if expected_shifts!=actual_shifts:
        errors.append(f'shifts.csv: 모든 근무일×직원 조합 필요; 누락 {len(expected_shifts-actual_shifts)}개, 초과 {len(actual_shifts-expected_shifts)}개')
    for line,r in table['demo_accounts.csv']:
        flag('demo_accounts.csv',line,r,'active')
        if r['role'] not in {'ADMIN','EMPLOYEE'}:errors.append(f'demo_accounts.csv:{line}: role 오류')
        if r['role']=='EMPLOYEE':has_key('demo_accounts.csv',line,'employee_id',r['employee_id'],employees)
        elif r['employee_id']:errors.append(f'demo_accounts.csv:{line}: ADMIN employee_id 공란 필요')
        if not r['initial_password']:errors.append(f'demo_accounts.csv:{line}: 임시 암호 누락')
    return errors

def main():
    p=argparse.ArgumentParser(description='Validate synthetic mock-assignment input datasets only')
    p.add_argument('dataset',type=Path);p.add_argument('--json',action='store_true')
    a=p.parse_args();issues=check(a.dataset)
    if a.json: print(json.dumps({'dataset':str(a.dataset),'ok':not issues,'errors':issues},ensure_ascii=False,indent=2))
    else:
        print(('PASS' if not issues else 'INVALID')+f': dataset={a.dataset} issues={len(issues)}')
        for e in issues[:50]:print(' - '+e)
        if len(issues)>50: print(f' ... and {len(issues)-50} additional issues')
    return 0 if not issues else 2

if __name__=='__main__':raise SystemExit(main())
