import unittest
from datetime import date
from decimal import Decimal

from pocket_money.validation import (ValidationError, parse_amount, parse_category,
                                     parse_date, parse_kind, parse_note, validate_record)

TODAY = date(2026, 11, 23)


class AmountTests(unittest.TestCase):
    def test_valid_amounts(self):
        self.assertEqual(parse_amount("120"), Decimal("120.00"))
        self.assertEqual(parse_amount("Rs. 1,250.5"), Decimal("1250.50"))
        self.assertEqual(parse_amount("0.01"), Decimal("0.01"))
        self.assertEqual(parse_amount("1000000"), Decimal("1000000.00"))

    def test_invalid_amounts(self):
        for bad in ["", "   ", "abc", "-5", "0", "0.001", "12.345", "NaN", "Infinity", "1000000.01", "1e400"]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                parse_amount(bad)


class DateTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_date("2026-11-01", TODAY), date(2026, 11, 1))
        self.assertEqual(parse_date("01-11-2026", TODAY), date(2026, 11, 1))
        self.assertEqual(parse_date("01/11/2026", TODAY), date(2026, 11, 1))

    def test_rejects_bad_dates(self):
        for bad in ["", "tomorrow", "2026-13-01", "2026-02-30", "2026-11-24", "1999-12-31"]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                parse_date(bad, TODAY)

    def test_today_is_allowed(self):
        self.assertEqual(parse_date("2026-11-23", TODAY), TODAY)


class TextTests(unittest.TestCase):
    def test_kind_aliases(self):
        self.assertEqual(parse_kind("I"), "income")
        self.assertEqual(parse_kind(" spent "), "expense")
        with self.assertRaises(ValidationError):
            parse_kind("loan")

    def test_category(self):
        self.assertEqual(parse_category("  food   court "), "Food Court")
        for bad in ["", "123", "a;drop", "x" * 31]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                parse_category(bad)

    def test_note_cleaning_and_limit(self):
        self.assertEqual(parse_note("a\x00b\n c"), "a b c")
        with self.assertRaises(ValidationError):
            parse_note("x" * 101)

    def test_validate_record_reports_missing(self):
        with self.assertRaises(ValidationError):
            validate_record({"date": "2026-11-01"}, TODAY)


if __name__ == "__main__":
    unittest.main()
