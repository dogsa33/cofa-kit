"""Tests for the optional human decision log; no external packages needed."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "decision_log.py"


class DecisionLogTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def cmd(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(self.root), *args],
                                text=True, capture_output=True, encoding="utf-8")
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertEqual(result.returncode, 2, result.stdout)
        return result

    def propose(self):
        self.cmd("propose", "--id", "D-001", "--topic", "합성 목표", "--option", "A::비용 감소",
                 "--option", "B::시간 감소", "--option", "C::균형", "--recommend", "B")

    def test_selection_rejected_not_selected_and_evidence(self):
        self.propose()
        self.cmd("select", "--id", "D-001", "--choice", "B", "--user-reply", "B로 진행해 줘",
                 "--reason", "시간을 우선", "--reject", "A::비용 절감을 최우선으로 하지 않음")
        self.cmd("implement", "--id", "D-001", "--file", "src/route.py", "--note", "사용자 목표 반영")
        self.cmd("verify", "--id", "D-001", "--status", "PASS", "--evidence", "python -m unittest -v")
        summary = self.cmd("report").stdout
        self.assertIn("대안 A: 명시적 거절", summary)
        self.assertIn("대안 B: 선택", summary)
        self.assertIn("대안 C: 미선택/미결정", summary)
        self.assertIn("src/route.py", summary)
        self.assertIn("PASS", summary)
        self.assertIn("B로 진행해 줘", summary)
        self.assertNotIn("**", summary)
        self.assertNotIn("##", summary)

    def test_requires_real_user_response_and_registered_choice(self):
        self.propose()
        self.cmd("select", "--id", "D-001", "--choice", "Z", "--user-reply", "Z", success=False)
        self.cmd("select", "--id", "D-001", "--choice", "B", "--user-reply", " ", success=False)
        self.assertNotIn("USER_REPORTED", (self.root / ".cofa-decisions.jsonl").read_text(encoding="utf-8"))

    def test_revise_keeps_old_history(self):
        self.propose()
        self.cmd("select", "--id", "D-001", "--choice", "A", "--user-reply", "A로 하자")
        self.cmd("verify", "--id", "D-001", "--status", "PASS", "--evidence", "기존 v1 검사")
        self.cmd("select", "--id", "D-001", "--choice", "B", "--user-reply", "B로 바꾸자", success=False)
        self.cmd("select", "--id", "D-001", "--choice", "B", "--user-reply", "B로 바꾸자", "--revise")
        events = [json.loads(s) for s in (self.root / ".cofa-decisions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([e.get("selected") for e in events if e["event"] == "SELECTED"], ["A", "B"])
        report = self.cmd("report").stdout
        self.assertIn("B로 바꾸자", report)
        self.assertIn("현재 선택 검증 아님", report)

    def test_pass_needs_evidence(self):
        self.propose()
        self.cmd("select", "--id", "D-001", "--choice", "A", "--user-reply", "A")
        self.cmd("verify", "--id", "D-001", "--status", "PASS", success=False)
        self.cmd("verify", "--id", "D-001", "--status", "NOT_RUN")

    def test_refuse_existing_report_and_corrupt_log(self):
        self.propose()
        self.cmd("report", "--output", "summary.md")
        self.cmd("report", "--output", "summary.md", success=False)
        (self.root / ".cofa-decisions.jsonl").write_text("{broken json\n", encoding="utf-8")
        self.cmd("propose", "--id", "D-002", "--topic", "새 문제", "--option", "A::a", "--option", "B::b", success=False)
        self.assertEqual((self.root / ".cofa-decisions.jsonl").read_text(encoding="utf-8"), "{broken json\n")

    def test_reject_cannot_include_selected(self):
        self.propose()
        self.cmd("select", "--id", "D-001", "--choice", "B", "--user-reply", "B", "--reject", "B::wrong", success=False)


if __name__ == "__main__":
    unittest.main()
