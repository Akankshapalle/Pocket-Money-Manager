import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pocket_money.ledger import Ledger
from pocket_money.storage import Storage

TODAY = date(2026, 11, 23)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "data.json"
        self.addCleanup(self.tmp.cleanup)

    def test_round_trip(self):
        led = Ledger()
        led.add("2026-11-01", "income", "Gift", "99.99", "hi", TODAY)
        led.set_budget("Food", "500")
        Storage(self.path).save(led)
        loaded, warnings = Storage(self.path).load()
        self.assertEqual(warnings, [])
        self.assertEqual(loaded.balance(), led.balance())
        self.assertEqual(loaded.budgets(), led.budgets())
        self.assertEqual(loaded.add("2026-11-02", "expense", "Food", "1", "", TODAY).id, 2)

    def test_missing_file_gives_empty_ledger(self):
        led, warnings = Storage(self.path).load()
        self.assertEqual((len(led), warnings), (0, []))

    def test_corrupted_json_is_quarantined(self):
        self.path.write_text("{ this is not json", encoding="utf-8")
        led, warnings = Storage(self.path).load()
        self.assertEqual(len(led), 0)
        self.assertTrue(warnings)
        self.assertFalse(self.path.exists())
        self.assertTrue(list(Path(self.tmp.name).glob("data.corrupt-*.json")))

    def test_bad_records_are_skipped_not_fatal(self):
        good = {"id": 1, "date": "2026-11-01", "kind": "income", "category": "Gift", "amount": "10.00"}
        bad = {"id": 2, "date": "nope", "kind": "income", "category": "Gift", "amount": "10"}
        dup = dict(good)
        self.path.write_text(json.dumps({"transactions": [good, bad, dup, "junk"]}), encoding="utf-8")
        led, warnings = Storage(self.path).load()
        self.assertEqual(len(led), 1)
        self.assertEqual(len(warnings), 3)

    def test_legacy_list_format(self):
        self.path.write_text(json.dumps([{"id": 1, "date": "2026-11-01", "kind": "expense",
                                          "category": "Food", "amount": "5"}]), encoding="utf-8")
        led, _ = Storage(self.path).load()
        self.assertEqual(len(led), 1)

    def test_no_temp_files_left_behind(self):
        Storage(self.path).save(Ledger())
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["data.json"])


if __name__ == "__main__":
    unittest.main()
