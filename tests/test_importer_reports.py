import csv
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from pocket_money.exporters import export_audit_log, export_csv, export_markdown
from pocket_money.importer import ImportFailure, import_csv, write_error_log
from pocket_money.ledger import Ledger
from pocket_money.reports import build_summary, render_text

TODAY = date(2026, 11, 23)
ROOT = Path(__file__).resolve().parent.parent


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rows, header=("date", "type", "category", "amount", "note")):
        p = self.dir / "in.csv"
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return p

    def test_mixed_file_reports_each_bad_row(self):
        p = self.write([["2026-11-01", "expense", "Food", "10", ""],
                        ["2026-11-02", "expense", "Food", "abc", ""],
                        ["2026-11-03", "bogus", "Food", "5", ""],
                        ["2026-11-01", "expense", "Food", "10", ""]])
        led = Ledger()
        res = import_csv(p, led)
        self.assertEqual((res.imported, res.skipped), (1, 3))
        self.assertEqual([n for n, _ in res.errors], [3, 4, 5])
        self.assertIn("Duplicate", res.errors[-1][1])
        log = write_error_log(res, p, self.dir / "e.log")
        self.assertIn("Row 3", log.read_text())

    def test_missing_columns_and_missing_file(self):
        with self.assertRaises(ImportFailure):
            import_csv(self.write([], header=("date", "amount")), Ledger())
        with self.assertRaises(ImportFailure):
            import_csv(self.dir / "nope.csv", Ledger())

    def test_extra_columns_flagged(self):
        p = self.write([["2026-11-01", "expense", "Food", "10", "", "surplus"]])
        self.assertEqual(import_csv(p, Ledger()).skipped, 1)

    def test_bundled_error_sample(self):
        res = import_csv(ROOT / "data" / "legacy_with_errors.csv", Ledger())
        self.assertEqual((res.imported, res.skipped), (2, 7))

    def test_bundled_clean_sample(self):
        led = Ledger()
        res = import_csv(ROOT / "data" / "sample_transactions.csv", led)
        self.assertEqual(res.skipped, 0)
        self.assertGreaterEqual(res.imported, 30)


class ReportTests(unittest.TestCase):
    def make(self):
        led = Ledger()
        led.add("2026-10-01", "income", "Allowance", "3000", "", TODAY)
        led.add("2026-10-10", "expense", "Food", "200", "", TODAY)
        led.add("2026-11-01", "income", "Allowance", "3000", "", TODAY)
        led.add("2026-11-11", "expense", "Food", "300", "", TODAY)
        return led

    def test_summary_numbers(self):
        s = build_summary(self.make(), TODAY)
        self.assertEqual(s["balance"], Decimal("5500.00"))
        self.assertEqual(s["avg_expense"], Decimal("250.00"))
        self.assertEqual(s["top_category"][0], "Food")
        self.assertEqual(s["status"], "HEALTHY")
        self.assertIn("up 50.0%", s["trend"])
        self.assertEqual(s["forecast_month_spend"], (Decimal("300") / 23 * 30).quantize(Decimal("0.01")))

    def test_empty_ledger_does_not_crash(self):
        s = build_summary(Ledger(), TODAY)
        self.assertEqual(s["balance"], Decimal("0.00"))
        self.assertIn("EXECUTIVE SUMMARY", render_text(s))

    def test_negative_balance_status(self):
        led = Ledger()
        led.add("2026-11-01", "expense", "Food", "10", "", TODAY)
        self.assertEqual(build_summary(led, TODAY)["status"], "CRITICAL")

    def test_exports_and_formula_injection_guard(self):
        led = self.make()
        led.add("2026-11-13", "expense", "Food", "5", "=SUM(A1)", TODAY)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            s = build_summary(led, TODAY)
            csv_path = export_csv(led, d / "a.csv")
            self.assertIn("'=SUM(A1)", csv_path.read_text())
            self.assertIn("| Balance |", export_markdown(s, led, d / "a.md").read_text())
            self.assertIn("ALL ENTRIES", export_audit_log(s, led, d / "a.txt").read_text())


if __name__ == "__main__":
    unittest.main()
