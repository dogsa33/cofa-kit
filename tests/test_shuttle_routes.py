"""Unit tests for the synthetic, independent shuttle constraint oracle."""
import copy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/shuttle"
SPEC = importlib.util.spec_from_file_location("shuttle_verifier", EXAMPLE / "verify_routes.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class ShuttleVerifierTests(unittest.TestCase):
    def setUp(self):
        self.workers, self.shifts, self.travel = verifier.load_dataset(EXAMPLE)
        self.result = json.loads((EXAMPLE / "routes_valid.json").read_text(encoding="utf-8"))

    def reasons(self, result):
        return verifier.validate(self.workers, self.shifts, self.travel, result)

    def test_valid_route_night_shift_and_directed_edges(self):
        self.assertEqual(self.reasons(self.result), [])
        self.assertNotEqual(self.travel[("S1", "PLANT_A")], self.travel[("PLANT_A", "S1")])
        self.assertEqual(self.shifts[("2026-11-04", "E03")]["end"].date().isoformat(), "2026-11-05")

    def test_missing_inbound_is_detected(self):
        self.result["trips"][0]["employee_ids"].remove("E02")
        self.assertTrue(any("MISSING_ASSIGN" in r and "E02 inbound" in r for r in self.reasons(self.result)))

    def test_duplicate_assignment_is_detected(self):
        duplicate = copy.deepcopy(self.result["trips"][0])
        duplicate["id"] = "T99"
        self.result["trips"].append(duplicate)
        self.assertTrue(any("DUP_ASSIGN" in r for r in self.reasons(self.result)))

    def test_off_day_must_not_be_assigned(self):
        self.result["trips"][0]["employee_ids"].append("E04")
        self.assertTrue(any("OFF_OR_UNKNOWN_SHIFT" in r for r in self.reasons(self.result)))

    def test_46_employees_in_45_seat_vehicle_are_rejected(self):
        # Synthetic 46-person case; duplicate employee IDs are not used.
        for idx in range(5, 49):
            eid = f"E{idx:02d}"
            self.workers[eid] = dict(self.workers["E01"], employee_id=eid)
            self.shifts[("2026-11-04", eid)] = dict(self.shifts[("2026-11-04", "E01")])
        # 2 employees + 44 additional employees = 46
        extras = [f"E{idx:02d}" for idx in range(5, 49)]
        self.result["trips"][0]["employee_ids"].extend(extras)
        self.result["trips"][1]["employee_ids"].extend(extras)
        errors = self.reasons(self.result)
        self.assertEqual(sum("CAPACITY:" in e for e in errors), 2)

    def test_early_departure_is_rejected(self):
        out = self.result["trips"][1]
        # Preserve travel duration so failure tests the shift constraint alone.
        for seg in out["legs"]:
            seg["depart_at"] = (verifier.local_time(seg["depart_at"]) - timedelta(minutes=10)).isoformat()
            seg["arrive_at"] = (verifier.local_time(seg["arrive_at"]) - timedelta(minutes=10)).isoformat()
        self.assertTrue(any("DEPART_EARLY" in e for e in self.reasons(self.result)))

    def test_arrival_after_deadline_is_rejected(self):
        inbound = self.result["trips"][0]
        for leg in inbound["legs"]:
            leg["depart_at"] = (verifier.local_time(leg["depart_at"]) + timedelta(minutes=30)).isoformat()
            leg["arrive_at"] = (verifier.local_time(leg["arrive_at"]) + timedelta(minutes=30)).isoformat()
        self.assertTrue(any("ARRIVAL_LATE" in e for e in self.reasons(self.result)))

    def test_wrong_directional_travel_time_is_detected(self):
        outbound = self.result["trips"][3]["legs"][0]
        outbound["arrive_at"] = (verifier.local_time(outbound["depart_at"]) + timedelta(minutes=20)).isoformat()
        self.assertTrue(any("TRAVEL_TIME" in e for e in self.reasons(self.result)))

    def test_overnight_outbound_on_wrong_calendar_day_is_rejected(self):
        overnight = self.result["trips"][3]["legs"][0]
        overnight["depart_at"] = "2026-11-04T07:15:00+09:00"
        overnight["arrive_at"] = "2026-11-04T07:40:00+09:00"
        self.assertTrue(any("DEPART_EARLY" in e for e in self.reasons(self.result)))

    def test_broken_route_connection_is_rejected(self):
        self.result["trips"][0]["legs"][1]["from"] = "S1"
        self.assertTrue(any("CONTINUITY" in e for e in self.reasons(self.result)))

    def test_malformed_schema_is_not_marked_pass(self):
        self.assertTrue(verifier.validate(self.workers, self.shifts, self.travel, {"trips": "wrong"}))

    def test_cli_runs_and_reports_pass(self):
        completed = subprocess.run([sys.executable, str(EXAMPLE / "verify_routes.py"),
                                    "--data-dir", str(EXAMPLE), "--routes", str(EXAMPLE / "routes_valid.json")],
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
