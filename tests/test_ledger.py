import unittest
from datetime import date
from decimal import Decimal

from pocket_money.ledger import Ledger
from pocket_money.validation import ValidationError

TODAY = date(2026, 11, 23)


def make():
    led = Ledger()
    led.add("2026-10-01", "income", "Allowance", "3000", "Oct", TODAY)
    led.add("2026-11-01", "income", "Allowance", "3000", "Nov", TODAY)
    led.add("2026-10-05", "expense", "Food", "100", "lunch", TODAY)
    led.add("2026-11-05", "expense", "Food", "150", "dinner out", TODAY)
    led.add("2026-11-06", "expense", "Travel", "60", "bus", TODAY)
    return led


class LedgerTests(unittest.TestCase):
    def test_balance_and_totals(self):
        led = make()
        self.assertEqual(led.total("income"), Decimal("6000.00"))
        self.assertEqual(led.total("expense"), Decimal("310.00"))
        self.assertEqual(led.balance(), Decimal("5690.00"))

    def test_decimal_precision(self):
        led = Ledger()
        for _ in range(10):
            led.add("2026-11-01", "expense", "Food", "0.10", "", TODAY)
        self.assertEqual(led.total("expense"), Decimal("1.00"))

    def test_rejects_invalid_add(self):
        with self.assertRaises(ValidationError):
            Ledger().add("2026-11-01", "expense", "Food", "-1", "", TODAY)

    def test_search_filters(self):
        led = make()
        self.assertEqual(len(led.search(category="food")), 2)
        self.assertEqual(len(led.search(keyword="BUS")), 1)
        self.assertEqual(len(led.search(kind="income")), 2)
        self.assertEqual(len(led.search(start=date(2026, 11, 1))), 3)
        self.assertEqual(led.search(category="food")[0].note, "dinner out")   # newest first
        self.assertEqual(led.search(category="Nothing"), [])

    def test_delete_updates_indexes(self):
        led = make()
        led.delete(3)
        self.assertEqual(len(led.search(category="Food")), 1)
        self.assertNotIn(3, [t.id for t in led.all()])
        with self.assertRaises(ValidationError):
            led.delete(999)

    def test_monthly_and_category_totals(self):
        led = make()
        self.assertEqual(led.monthly_totals()[1], ("2026-11", Decimal("3000.00"), Decimal("210.00")))
        self.assertEqual(list(led.category_totals())[0], "Food")

    def test_duplicate_detection(self):
        led = make()
        rec = {"date": date(2026, 11, 6), "kind": "expense", "category": "Travel",
               "amount": Decimal("60.00"), "note": "bus"}
        self.assertTrue(led.is_duplicate(rec))
        rec["note"] = "taxi"
        self.assertFalse(led.is_duplicate(rec))

    def test_budget_alerts(self):
        led = make()
        led.set_budget("Food", "170")
        msgs = [a for a in led.alerts(TODAY) if "Food" in a.message]
        self.assertEqual(msgs[0].level, "WARNING")          # 150/170 = 88%
        led.set_budget("Food", "100")
        self.assertEqual([a.level for a in led.alerts(TODAY) if "Food" in a.message], ["CRITICAL"])

    def test_low_and_negative_balance(self):
        led = Ledger()
        led.add("2026-11-01", "income", "Gift", "50", "", TODAY)
        self.assertTrue(any("below" in a.message for a in led.alerts(TODAY)))
        led.add("2026-11-02", "expense", "Food", "80", "", TODAY)
        self.assertTrue(any(a.level == "CRITICAL" for a in led.alerts(TODAY)))

    def test_anomaly_detection(self):
        led = Ledger()
        for d in range(1, 7):
            led.add(f"2026-11-0{d}", "expense", "Snacks", "20", "", TODAY)
        led.add("2026-11-10", "expense", "Snacks", "500", "splurge", TODAY)
        flagged = led.anomalies()
        self.assertEqual([t.note for t in flagged], ["splurge"])

    def test_recurring_is_idempotent_and_catches_up(self):
        led = Ledger()
        led.add_recurring("income", "Allowance", "3000", 1)
        created = led.apply_recurring(date(2026, 11, 23))
        self.assertEqual(len(created), 1)
        self.assertEqual(led.apply_recurring(date(2026, 11, 23)), [])       # no duplicates
        later = led.apply_recurring(date(2027, 2, 15))                      # Dec, Jan, Feb
        self.assertEqual([t.date for t in later], [date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1)])

    def test_recurring_clamps_day_in_short_month(self):
        led = Ledger()
        led.add_recurring("expense", "Rent", "100", 31)
        led.settings["recurring"][0]["last_applied"] = "2027-01"
        created = led.apply_recurring(date(2027, 3, 1))
        self.assertEqual([t.date for t in created], [date(2027, 2, 28)])


if __name__ == "__main__":
    unittest.main()
