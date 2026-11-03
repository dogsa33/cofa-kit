"""Protect original input files without blocking legitimate new output files."""
import importlib.util
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cofa_source_guard", ROOT / "scripts/source_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        # The intentional FAIL/NOT_RUN outputs below are negative-test fixtures,
        # not failures of the unit-test suite; keep the final console summary clear.
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def test_snapshot_check_original_change_and_new_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text("task description", encoding="utf-8")
            (root / "data.csv").write_text("x\n1\n", encoding="utf-8")
            self.assertEqual(guard.snapshot(root, ["README.md", "data.csv"]), 0)
            self.assertEqual(guard.check(root), 0)
            (root / "output.csv").write_text("y\n2\n", encoding="utf-8")
            self.assertEqual(guard.check(root), 0)
            (root / "data.csv").write_text("x\n3\n", encoding="utf-8")
            self.assertEqual(guard.check(root), 1)

    def test_repeated_snapshot_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data.csv").write_text("1", encoding="utf-8")
            guard.snapshot(root, ["data.csv"])
            original = (root / guard.MANIFEST).read_bytes()
            with self.assertRaises(ValueError):
                guard.snapshot(root, ["data.csv"])
            self.assertEqual((root / guard.MANIFEST).read_bytes(), original)

    def test_traversal_or_missing_input_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError):
                guard.snapshot(root, ["../outside.csv"])
            with self.assertRaises(ValueError):
                guard.snapshot(root, ["missing.csv"])
            self.assertEqual(guard.check(root), 2)


if __name__ == "__main__":
    unittest.main()
