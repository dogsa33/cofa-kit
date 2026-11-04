"""Test only the supplied input fixtures. These tests DO NOT grade any participant web app."""
from pathlib import Path
import sys,unittest,csv,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_datasets import check

class FixtureContract(unittest.TestCase):
    def test_base_valid(self):self.assertEqual(check(ROOT/'datasets/base'),[])
    def test_shift_changed_valid(self):self.assertEqual(check(ROOT/'datasets/S1_shift_changed'),[])
    def test_travel_changed_valid(self):self.assertEqual(check(ROOT/'datasets/S2_travel_changed'),[])
    def test_stop_disabled_valid(self):self.assertEqual(check(ROOT/'datasets/S3_stop_disabled'),[])
    def test_employee_moved_valid(self):self.assertEqual(check(ROOT/'datasets/S4_employee_moved'),[])
    def test_vehicle_disabled_valid(self):self.assertEqual(check(ROOT/'datasets/S5_vehicle_disabled'),[])
    def test_missing_header_invalid(self):self.assertTrue(any('site_id' in x for x in check(ROOT/'datasets/E1_missing_column')))
    def test_invalid_foreign_key(self):self.assertTrue(any('UNKNOWN_999' in x for x in check(ROOT/'datasets/E2_bad_foreign_key')))
    def test_invalid_clock(self):self.assertTrue(any('25:99' in x for x in check(ROOT/'datasets/E3_bad_shift_time')))
    def test_missing_directed_edge(self):self.assertTrue(any('방향 간선 누락' in x for x in check(ROOT/'datasets/E4_missing_travel_edge')))
    def test_directional_graph_is_not_assumed_symmetric(self):
        with (ROOT/'datasets/base/travel_times.csv').open(encoding='utf-8-sig',newline='') as f:
            edges={(r['from_node_id'],r['to_node_id']):int(r['minutes']) for r in csv.DictReader(f)}
        self.assertTrue(any(x!=y and edges[(x,y)]!=edges[(y,x)] for x,y in edges))
    def test_shift_changed_not_same_data(self):
        def read(p):
            with p.open(encoding='utf-8-sig',newline='') as f:return {(r['shift_date'],r['employee_id']):r['status'] for r in csv.DictReader(f)}
        a=read(ROOT/'datasets/base/shifts.csv');b=read(ROOT/'datasets/S1_shift_changed/shifts.csv')
        delta=[k for k in a if a[k]!=b[k]]
        self.assertEqual(len(delta),3)
        self.assertTrue(all(x[0]=='2026-11-10' for x in delta))
    def test_travel_changed_directional_not_global_symmetric(self):
        def read(p):
            with p.open(encoding='utf-8-sig',newline='') as f:return {(r['from_node_id'],r['to_node_id']):int(r['minutes']) for r in csv.DictReader(f)}
        a=read(ROOT/'datasets/base/travel_times.csv');b=read(ROOT/'datasets/S2_travel_changed/travel_times.csv')
        changed=[k for k in a if a[k]!=b[k]]
        self.assertGreaterEqual(len(changed),20)
        self.assertTrue(any((y,x) not in changed for x,y in changed))
    def test_no_solution_source_is_bundled(self):
        self.assertFalse((ROOT/'src').exists());self.assertFalse((ROOT/'app').exists())
        self.assertFalse((ROOT/'artifacts/route_plan.json').exists())

if __name__=='__main__':unittest.main()
