"""Regenerates data/sample_transactions.csv, sample_transactions.json and a CSV with deliberate errors.
Run from the project root:  python scripts/make_sample_data.py"""
import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pocket_money.ledger import Ledger          # noqa: E402
from pocket_money.storage import Storage       # noqa: E402

random.seed(14)
rows = []
start = date(2026, 9, 1)
for month_start in (date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)):
    rows.append((month_start, "income", "Allowance", "3000.00", "Monthly allowance from parents"))
rows += [
    (date(2026, 9, 14), "income", "Gift", "500.00", "Birthday money"),
    (date(2026, 10, 9), "income", "Part-time Work", "1200.00", "Weekend tutoring"),
    (date(2026, 11, 8), "income", "Gift", "0.01", "Boundary: smallest amount"),
]
spend = {"Food": (40, 180, "Canteen"), "Transport": (20, 90, "Bus/metro"),
         "Stationery": (15, 250, "Notebooks/pens"), "Entertainment": (100, 450, "Movie/games"),
         "Snacks": (10, 60, "Evening snacks"), "Recharge": (199, 299, "Mobile recharge")}
for _ in range(33):
    cat = random.choice(list(spend))
    lo, hi, note = spend[cat]
    when = start + timedelta(days=random.randint(0, 79))
    rows.append((when, "expense", cat, f"{random.uniform(lo, hi):.2f}", note))
rows.append((date(2026, 10, 20), "expense", "Entertainment", "2500.00", "Edge case: unusually large (anomaly)"))
rows.append((date(2026, 11, 20), "expense", "Snacks", "0.01", "Edge case: smallest expense"))
rows.sort(key=lambda r: r[0])

data = ROOT / "data"
data.mkdir(exist_ok=True)
with open(data / "sample_transactions.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "type", "category", "amount", "note"])
    for d, k, c, a, n in rows:
        w.writerow([d.isoformat(), k, c, a, n])

ledger = Ledger()
for d, k, c, a, n in rows:
    ledger.add(d, k, c, a, n, today=date(2026, 11, 23))
ledger.set_budget("Entertainment", "1000")
Storage(data / "sample_transactions.json").save(ledger)

with open(data / "legacy_with_errors.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "type", "category", "amount", "note"])
    w.writerows([
        ["2026-11-01", "expense", "Food", "120.50", "valid row"],
        ["2026-11-02", "expense", "Food", "abc", "non-numeric amount"],
        ["2026-11-03", "spent", "Transport", "-40", "negative amount"],
        ["2099-01-01", "expense", "Food", "10", "future date"],
        ["2026-11-04", "income", "", "100", "blank category"],
        ["2026-11-05", "income", "Gift", "250", "valid row"],
        ["not-a-date", "expense", "Food", "10", "bad date"],
        ["2026-11-06", "expense", "Snacks", "12.345", "too many decimals"],
        ["2026-11-01", "expense", "Food", "120.50", "valid row"],
    ])
print(f"Wrote {len(rows)} sample rows.")
