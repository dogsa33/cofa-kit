"""Independent checks against original published synthetic expected values."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/data_tools.py'
SPEC=importlib.util.spec_from_file_location('data_tools',SCRIPT)
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)


class OriginalDataExamples(unittest.TestCase):
    def test_original_csv_sample_counts(self):
        r=mod.profile(ROOT/'examples/defects.csv')
        self.assertEqual(r['rows'],5)
        self.assertEqual(r['duplicate_rows_in_sample'],1)
        self.assertEqual(r['columns']['inspected']['missing'],1)
        self.assertTrue(r['full_scan'])

    def test_profile_bounded_never_claims_all(self):
        r=mod.profile(ROOT/'examples/defects.csv',2)
        self.assertEqual(r['sampled_rows'],2)
        self.assertFalse(r['full_scan'])

    def test_join_valid_map_matches_original_expected(self):
        e=ROOT/'examples/joins'; ref=json.loads((e/'expected.json').read_text(encoding='utf-8'))
        x=mod.audit_join(e/'inspections.csv',e/'tool_map.csv',['lot_id','wafer_id'],['lot_id','wafer_id'],'many_to_one')
        self.assertTrue(x['ok']);self.assertEqual(x['predicted_rows'],ref['inspections_to_tool_map']['predicted_rows'])

    def test_join_row_multiplication_and_invalid_cardinality(self):
        e=ROOT/'examples/joins'; ref=json.loads((e/'expected.json').read_text(encoding='utf-8'))
        x=mod.audit_join(e/'inspections.csv',e/'defects.csv',['lot_id','wafer_id'],['lot_id','wafer_id'],'many_to_one')
        self.assertFalse(x['ok'])
        self.assertEqual(x['right_duplicate_keys'],1)
        self.assertEqual(x['predicted_rows'],ref['inspections_to_defects']['predicted_rows'])
        self.assertEqual(x['left_unmatched_rows'],1)

    def test_weighted_yield_matches_original_expected(self):
        e=ROOT/'examples/semiconductor';ref=json.loads((e/'expected.json').read_text(encoding='utf-8'))['yield_clean']
        x=mod.weighted_yield(e/'yield_clean.csv')
        for group in ('TOOL-A','TOOL-B'):
            self.assertEqual(x['groups'][group]['tested'],ref[group]['tested'])
            self.assertEqual(x['groups'][group]['passed'],ref[group]['passed'])
            self.assertAlmostEqual(x['groups'][group]['pass_rate_pct'],ref[group]['pass_rate_pct'])
        self.assertEqual(x['totals'],ref['totals'])

    def test_duplicate_composite_key_is_blocked(self):
        with self.assertRaisesRegex(mod.DataError,'duplicate composite key'):
            mod.weighted_yield(ROOT/'examples/semiconductor/yield_dirty.csv')

    def test_spc_matches_original_expected(self):
        e=ROOT/'examples/semiconductor';ref=json.loads((e/'expected.json').read_text(encoding='utf-8'))['measurements_baseline_25']
        x=mod.imr(e/'measurements.csv',baseline_count=25)
        for k in ('mean','mr_bar','i_lcl','i_ucl','mr_ucl'):
            self.assertAlmostEqual(x['baseline'][k],ref[k])
        self.assertEqual(x['evaluation'],ref['evaluation'])

    def test_spc_out_of_order_times_fail(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data.csv';p.write_text('timestamp,value\n2026-01-02T00:00:00+09:00,1\n2026-01-01T00:00:00+09:00,2\n2026-01-03T00:00:00+09:00,3\n2026-01-04T00:00:00+09:00,4\n',encoding='utf-8')
            with self.assertRaisesRegex(mod.DataError,'increasing'):
                mod.imr(p,baseline_count=3)

    def test_nan_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data.csv';p.write_text('timestamp,value\n2026-01-01T00:00:00+09:00,1\n2026-01-02T00:00:00+09:00,NaN\n2026-01-03T00:00:00+09:00,3\n2026-01-04T00:00:00+09:00,4\n',encoding='utf-8')
            with self.assertRaisesRegex(mod.DataError,'finite'):
                mod.imr(p,baseline_count=3)

    def test_unknown_header_and_bad_shape(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'broken.csv';p.write_text('a,a\n1,2\n',encoding='utf-8')
            with self.assertRaises(mod.DataError):mod.read_rows(p)
            p.write_text('a,b\n1,2,3\n',encoding='utf-8')
            with self.assertRaises(mod.DataError):mod.read_rows(p)

    def test_cli_errors_not_reported_success(self):
        p=subprocess.run([sys.executable,'-X','utf8',str(SCRIPT),'yield',str(ROOT/'examples/semiconductor/yield_dirty.csv')],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(p.returncode,2)
        self.assertIn('INPUT_ERROR',p.stderr)

    def test_data_format_is_still_original(self):
        self.assertEqual((ROOT/'examples/semiconductor/yield_clean.csv').read_text(encoding='utf-8').splitlines()[0],
                         'lot_id,wafer_id,tool_id,tested,passed')
        self.assertEqual((ROOT/'examples/joins/inspections.csv').read_text(encoding='utf-8').splitlines()[0],
                         'lot_id,wafer_id,tested,passed')

if __name__=='__main__':unittest.main()
