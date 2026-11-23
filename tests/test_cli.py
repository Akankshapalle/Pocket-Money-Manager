"""End-to-end test of the menu loop with scripted keyboard input."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pocket_money.cli import main
from pocket_money.storage import Storage


class CliTests(unittest.TestCase):
    def run_cli(self, answers, tmp):
        out = io.StringIO()
        args = ["--data", str(Path(tmp) / "d.json"), "--reports", str(Path(tmp) / "r")]
        with mock.patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(out):
            main(args)
        return out.getvalue()

    def test_validation_loop_then_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_cli(["1",
                                "x", "e",                          # bad type, then valid
                                "31-02-2026", "2026-11-01",        # impossible date, then valid
                                "Food",
                                "abc", "-4", "75.5",               # two bad amounts, then valid
                                "lunch", "0"], tmp)
            self.assertEqual(out.count("[!]"), 4)
            self.assertIn("Saved entry #1", out)
            ledger, _ = Storage(Path(tmp) / "d.json").load()
            self.assertEqual(len(ledger), 1)
            out2 = self.run_cli(["2", "0"], tmp)                   # relaunch: data survives
            self.assertIn("lunch", out2)

    def test_unknown_menu_choice_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_cli(["zzz", "", "0"], tmp)
            self.assertIn("Please enter a number", out)

    def test_demo_summary_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            args = ["--demo", "--data", str(Path(tmp) / "d.json"), "--reports", str(Path(tmp) / "r")]
            with mock.patch("builtins.input", side_effect=["4", "7", "0"]), contextlib.redirect_stdout(out):
                main(args)
            text = out.getvalue()
            self.assertIn("EXECUTIVE SUMMARY", text)
            self.assertTrue(list((Path(tmp) / "r").glob("audit_*.txt")))


if __name__ == "__main__":
    unittest.main()
