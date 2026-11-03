"""Regression guards: unambiguous human selection and manual evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/decision_log.py"


class HumanGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_cli("propose", "--id", "D-001", "--topic", "목적함수", "--option", "A::차량 수", "--option", "B::탑승 시간", "--recommend", "B")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(self.root), *args], capture_output=True, text=True, encoding="utf-8")

    def test_also_rejects_delegated_answer_not_explicit_selection(self):
        for answer in ("알아서", "네가 결정해", "추천대로", "그냥 해", "PASS", "FAIL", "NOT_RUN", "통과", "  "):
            r = self.run_cli("select", "--id", "D-001", "--choice", "A", "--user-reply", answer)
            self.assertEqual(r.returncode, 2, f"{answer}: {r.stdout} {r.stderr}")
        events = [json.loads(x) for x in (self.root / ".cofa-decisions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([x["event"] for x in events], ["PROPOSED"])

    def test_pass_without_meaningful_evidence_is_rejected(self):
        self.assertEqual(self.run_cli("select", "--id", "D-001", "--choice", "B", "--user-reply", "B로 진행").returncode, 0)
        self.assertEqual(self.run_cli("verify", "--id", "D-001", "--status", "PASS", "--evidence", " ").returncode, 2)

    def test_implementation_cannot_precede_user_answer(self):
        r = self.run_cli("implement", "--id", "D-001", "--file", "server.py")
        self.assertEqual(r.returncode, 2)

    def test_manual_check_requires_evidence_then_accepts_explicit_user_answer(self):
        r = self.run_cli("select", "--id", "D-001", "--choice", "B", "--user-reply", "B로 진행")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("verify", "--id", "D-001", "--status", "HUMAN_CHECK")
        self.assertEqual(r.returncode, 2)
        r = self.run_cli("verify", "--id", "D-001", "--status", "HUMAN_CHECK", "--evidence", "사용자 UAT-01 실제 화면 확인: PASS")
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
