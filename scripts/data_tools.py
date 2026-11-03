#!/usr/bin/env python3
"""Small offline CSV diagnostics for practice: profile, key join audit, weighted yield, I-MR.
No network, external packages, database writes, or task-specific policy decisions.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys


class DataError(ValueError):
    pass


def read_rows(path: str | Path, required: list[str] | tuple[str, ...] = (), encoding: str = 'utf-8-sig') -> tuple[list[str], list[dict[str, str]]]:
    p = Path(path)
    if not p.is_file():
        raise DataError(f'File not found: {p}')
    with p.open('r', encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
            raise DataError('CSV header missing/duplicated/blank')
        missing = set(required) - set(headers)
        if missing:
            raise DataError(f'Missing columns: {sorted(missing)}')
        rows = []
        for line, row in enumerate(reader, 2):
            if None in row or any(val is None for val in row.values()):
                raise DataError(f'Malformed CSV row at line {line}')
            rows.append(row)
    return headers, rows


def profile(path: str | Path, max_rows: int = 10000, encoding: str = 'utf-8-sig') -> dict:
    if type(max_rows) is not int or not 1 <= max_rows <= 100000:
        raise DataError('max_rows outside 1..100000')
    header, data = read_rows(path, encoding=encoding)
    sampled = data[:max_rows]
    cols = {}
    for col in header:
        values = [row[col] for row in sampled]
        nonempty = [v for v in values if v.strip()]
        unique = len(set(values))
        nums = []
        for value in nonempty:
            try:
                num = float(value)
                if math.isfinite(num):
                    nums.append(num)
            except ValueError:
                pass
        cols[col] = {'missing': len(values) - len(nonempty), 'unique': unique,
                     'numeric_min': min(nums) if nums else None, 'numeric_max': max(nums) if nums else None}
    # No raw values are echoed; do not mistake sample for full-file validation.
    return {'rows': len(data), 'sampled_rows': len(sampled), 'full_scan': len(sampled) == len(data),
            'duplicate_rows_in_sample': len(sampled) - len({tuple(row[c] for c in header) for row in sampled}),
            'columns': cols, 'limits': 'Counts and ranges are descriptive, not business-rule validation.'}


def audit_join(left: str | Path, right: str | Path, left_key: list[str], right_key: list[str], relationship: str = 'many_to_one') -> dict:
    if not left_key or len(left_key) != len(right_key) or relationship not in {'one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'}:
        raise DataError('Key lengths/relationship invalid')
    _, lrows = read_rows(left, left_key)
    _, rrows = read_rows(right, right_key)
    if any(any(not row[c].strip() for c in left_key) for row in lrows) or any(any(not row[c].strip() for c in right_key) for row in rrows):
        raise DataError('Empty join key')
    lcount, rcount = Counter(tuple(r[k] for k in left_key) for r in lrows), Counter(tuple(r[k] for k in right_key) for r in rrows)
    keys = set(lcount) | set(rcount)
    inner = sum(lcount[k]*rcount[k] for k in keys)
    lunmatched = sum(lcount[k] for k in lcount if k not in rcount)
    runmatched = sum(rcount[k] for k in rcount if k not in lcount)
    lduplicates = sum(n > 1 for n in lcount.values())
    rduplicates = sum(n > 1 for n in rcount.values())
    ok = ((relationship in {'one_to_many', 'one_to_one'} or not rduplicates)
          and (relationship in {'many_to_one', 'many_to_many'} or not lduplicates))
    # Predicted row counts account for unmatched outer-join records, not data-value conservation.
    return {'relationship': relationship, 'ok': bool(ok), 'left_rows': len(lrows), 'right_rows': len(rrows),
            'left_duplicate_keys': lduplicates, 'right_duplicate_keys': rduplicates,
            'left_unmatched_rows': lunmatched, 'right_unmatched_rows': runmatched,
            'predicted_rows': {'inner': inner, 'left': inner+lunmatched,
                               'right': inner+runmatched, 'full': inner+lunmatched+runmatched},
            'warning': 'A join audit checks key cardinality, not whether business totals are preserved.'}


def weighted_yield(path: str | Path, group_col: str = 'tool_id', key_cols: list[str] | None = None,
                   tested_col: str = 'tested', passed_col: str = 'passed') -> dict:
    keys = key_cols or ['lot_id','wafer_id']
    _, rows = read_rows(path, [group_col, *keys, tested_col, passed_col])
    groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    seen = set()
    for row in rows:
        key = tuple(row[c] for c in keys)
        if any(not value.strip() for value in key) or key in seen:
            raise DataError('duplicate composite key or empty key')
        seen.add(key)
        try:
            tested, passed = int(row[tested_col]), int(row[passed_col])
        except ValueError as exc:
            raise DataError('Invalid counts') from exc
        if tested < 0 or passed < 0 or passed > tested:
            raise DataError('Counts must satisfy 0 <= passed <= tested')
        group = row[group_col]
        groups[group][0] += tested
        groups[group][1] += passed
    if not rows:
        raise DataError('Zero data rows')
    def summarize(t, p):
        return {'tested': t, 'passed': p, 'pass_rate_pct': p*100/t if t else None}
    result = {g: summarize(*v) for g,v in sorted(groups.items())}
    return {'groups': result, 'totals': summarize(sum(v[0] for v in groups.values()), sum(v[1] for v in groups.values()))}


def imr(path: str | Path, *, baseline_count: int, value_col: str='value', time_col: str='timestamp') -> dict:
    _, rows = read_rows(path,[value_col,time_col])
    if type(baseline_count) is not int or baseline_count < 3 or len(rows) <= baseline_count:
        raise DataError('Need >=3 baseline and at least one evaluation row')
    times=[]; values=[]
    for row in rows:
        try:
            val=float(row[value_col]); at=datetime.fromisoformat(row[time_col])
        except (ValueError, TypeError) as exc:
            raise DataError('Invalid value/timestamp') from exc
        if not math.isfinite(val) or at.tzinfo is None or at.utcoffset() is None:
            raise DataError('Expected finite values and offset-aware timestamps')
        values.append(val);times.append(at)
    if any(a>=b for a,b in zip(times,times[1:])):
        raise DataError('Timestamps must be strictly increasing')
    baseline=values[:baseline_count]
    mean=sum(baseline)/baseline_count
    ranges=[abs(a-b) for a,b in zip(baseline,baseline[1:])]
    mr=sum(ranges)/len(ranges)
    if mr <= 0:
        raise DataError('Zero moving range: control limits indeterminate')
    lcl,ucl = mean-3*mr/1.128,mean+3*mr/1.128
    mr_ucl=3.267*mr
    results=[]
    for i in range(baseline_count,len(values)):
        mr_i=abs(values[i]-values[i-1])
        results.append({'row_number':i+1,'value':values[i], 'moving_range':mr_i,
                        'i_signal':values[i]<lcl or values[i]>ucl,'mr_signal':mr_i>mr_ucl})
    return {'baseline':{'count':baseline_count,'mean':mean,'mr_bar':mr,'i_lcl':lcl,'i_ucl':ucl,'mr_ucl':mr_ucl},
            'evaluation':results,'warning':'I-MR signals are not defect labels or proven causes.'}


def cli():
    ap=argparse.ArgumentParser(description=__doc__)
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('profile');p.add_argument('csv');p.add_argument('--max-rows',type=int,default=10000)
    p=sp.add_parser('join');p.add_argument('left');p.add_argument('right');p.add_argument('--left-key',nargs='+',required=True);p.add_argument('--right-key',nargs='+',required=True);p.add_argument('--relationship',default='many_to_one')
    p=sp.add_parser('yield');p.add_argument('csv');p.add_argument('--group',default='tool_id');p.add_argument('--key',nargs='+',default=['lot_id','wafer_id'])
    p=sp.add_parser('spc');p.add_argument('csv');p.add_argument('--baseline-count',type=int,required=True)
    args=ap.parse_args()
    try:
        if args.cmd=='profile': out=profile(args.csv,args.max_rows)
        elif args.cmd=='join': out=audit_join(args.left,args.right,args.left_key,args.right_key,args.relationship)
        elif args.cmd=='yield':out=weighted_yield(args.csv,args.group,args.key)
        else:out=imr(args.csv,baseline_count=args.baseline_count)
        print(json.dumps(out,ensure_ascii=False,indent=2))
    except (OSError,DataError,UnicodeError,csv.Error) as exc:
        print('INPUT_ERROR:',exc,file=sys.stderr);return 2
    return 0


if __name__=='__main__':
    for st in (sys.stdout,sys.stderr):
        if hasattr(st,'reconfigure'):st.reconfigure(encoding='utf-8',errors='replace')
    raise SystemExit(cli())
