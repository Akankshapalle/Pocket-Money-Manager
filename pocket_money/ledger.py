"""Business logic: the Ledger holds transactions, indexes and budget rules."""
import calendar
import statistics
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional

from .models import Alert, EXPENSE, INCOME, Transaction
from .validation import (ValidationError, parse_amount, parse_category,
                         parse_day_of_month, parse_kind, validate_record)

ANOMALY_FACTOR = Decimal("2.5")   # expense > 2.5 x category median is "unusual"
ANOMALY_MIN_ENTRIES = 5
BUDGET_WARN_RATIO = Decimal("0.8")


def default_settings() -> dict:
    return {"budgets": {}, "low_balance_threshold": "100.00", "recurring": []}


class Ledger:
    """In-memory store with secondary indexes (by category and by month)
    so searches and monthly reports do not scan every record."""

    def __init__(self, transactions: Iterable[Transaction] = (), settings: Optional[dict] = None):
        self._tx = {}
        self._by_category = defaultdict(set)
        self._by_month = defaultdict(set)
        self.settings = default_settings()
        if settings:
            self.settings.update({k: v for k, v in settings.items() if k in self.settings})
        for t in transactions:
            self._index(t)
        self._next_id = max(self._tx, default=0) + 1

    # ---------- indexing ----------
    def _index(self, t: Transaction) -> None:
        self._tx[t.id] = t
        self._by_category[t.category].add(t.id)
        self._by_month[t.month].add(t.id)

    def _unindex(self, t: Transaction) -> None:
        del self._tx[t.id]
        self._by_category[t.category].discard(t.id)
        self._by_month[t.month].discard(t.id)

    # ---------- CRUD ----------
    def __len__(self) -> int:
        return len(self._tx)

    def add(self, when, kind, category, amount, note="", today: date = None) -> Transaction:
        rec = validate_record({"date": when, "kind": kind, "category": category,
                               "amount": amount, "note": note}, today)
        t = Transaction(self._next_id, **rec)
        self._next_id += 1
        self._index(t)
        return t

    def delete(self, tx_id: int) -> Transaction:
        if tx_id not in self._tx:
            raise ValidationError(f"No entry with id {tx_id}.")
        t = self._tx[tx_id]
        self._unindex(t)
        return t

    def get(self, tx_id: int) -> Optional[Transaction]:
        return self._tx.get(tx_id)

    def all(self) -> List[Transaction]:
        return sorted(self._tx.values(), key=lambda t: (t.date, t.id))

    def is_duplicate(self, rec: dict) -> bool:
        for tid in self._by_month.get(rec["date"].strftime("%Y-%m"), ()):
            t = self._tx[tid]
            if (t.date, t.kind, t.category, t.amount, t.note) == (
                    rec["date"], rec["kind"], rec["category"], rec["amount"], rec["note"]):
                return True
        return False

    # ---------- queries ----------
    def search(self, keyword=None, category=None, kind=None, start=None, end=None) -> List[Transaction]:
        if category:
            ids = self._by_category.get(parse_category(category), set())   # index lookup
        else:
            ids = self._tx.keys()
        kind = parse_kind(kind) if kind else None
        kw = keyword.strip().lower() if keyword else None
        out = []
        for tid in ids:
            t = self._tx[tid]
            if kind and t.kind != kind:
                continue
            if start and t.date < start:
                continue
            if end and t.date > end:
                continue
            if kw and kw not in f"{t.category} {t.note}".lower():
                continue
            out.append(t)
        return sorted(out, key=lambda t: (t.date, t.id), reverse=True)

    def categories(self) -> List[str]:
        return sorted(c for c, ids in self._by_category.items() if ids)

    # ---------- aggregates ----------
    def total(self, kind: str, txs: Optional[Iterable[Transaction]] = None) -> Decimal:
        txs = self._tx.values() if txs is None else txs
        return sum((t.amount for t in txs if t.kind == kind), Decimal("0.00"))

    def balance(self) -> Decimal:
        return self.total(INCOME) - self.total(EXPENSE)

    def monthly_totals(self) -> list:
        """[(YYYY-MM, income, expense)] in chronological order."""
        rows = []
        for month in sorted(m for m, ids in self._by_month.items() if ids):
            txs = [self._tx[i] for i in self._by_month[month]]
            rows.append((month, self.total(INCOME, txs), self.total(EXPENSE, txs)))
        return rows

    def category_totals(self, kind: str = EXPENSE) -> dict:
        out = {}
        for cat, ids in self._by_category.items():
            amount = self.total(kind, (self._tx[i] for i in ids))
            if amount:
                out[cat] = amount
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    def month_spend(self, category: str, month: str) -> Decimal:
        ids = self._by_category.get(category, set()) & self._by_month.get(month, set())
        return self.total(EXPENSE, (self._tx[i] for i in ids))

    def balance_history(self) -> list:
        """[(date, running balance)] one point per day that has activity."""
        running, points = Decimal("0.00"), {}
        for t in self.all():
            running += t.amount if t.kind == INCOME else -t.amount
            points[t.date] = running
        return list(points.items())

    # ---------- settings: budgets, thresholds, recurring ----------
    def set_budget(self, category: str, amount) -> None:
        self.settings["budgets"][parse_category(category)] = str(parse_amount(amount))

    def remove_budget(self, category: str) -> None:
        self.settings["budgets"].pop(parse_category(category), None)

    def budgets(self) -> dict:
        return {c: Decimal(a) for c, a in self.settings["budgets"].items()}

    def set_low_balance_threshold(self, amount) -> None:
        self.settings["low_balance_threshold"] = str(parse_amount(amount))

    def add_recurring(self, kind, category, amount, day, note="Recurring") -> None:
        self.settings["recurring"].append({
            "kind": parse_kind(kind), "category": parse_category(category),
            "amount": str(parse_amount(amount)), "day": parse_day_of_month(day),
            "note": note, "last_applied": None})

    def apply_recurring(self, today: date = None) -> List[Transaction]:
        """Create any recurring entries that have come due. Safe to call repeatedly."""
        today = today or date.today()
        created = []
        for rule in self.settings["recurring"]:
            for due in self._due_dates(rule, today):
                created.append(self.add(due, rule["kind"], rule["category"],
                                        rule["amount"], rule["note"], today))
                rule["last_applied"] = due.strftime("%Y-%m")
        return created

    @staticmethod
    def _due_dates(rule: dict, today: date):
        if rule.get("last_applied"):
            y, m = map(int, rule["last_applied"].split("-"))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        else:
            y, m = today.year, today.month
        while (y, m) <= (today.year, today.month):
            due = date(y, m, min(rule["day"], calendar.monthrange(y, m)[1]))
            if due > today:
                break
            yield due
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    # ---------- warnings ----------
    def anomalies(self) -> List[Transaction]:
        """Expenses far above the usual size for their category (median-based, outlier-resistant)."""
        flagged = []
        for cat, ids in self._by_category.items():
            exp = [self._tx[i] for i in ids if self._tx[i].kind == EXPENSE]
            if len(exp) < ANOMALY_MIN_ENTRIES:
                continue
            median = statistics.median(t.amount for t in exp)
            flagged += [t for t in exp if t.amount > median * ANOMALY_FACTOR]
        return sorted(flagged, key=lambda t: (t.date, t.id), reverse=True)

    def alerts(self, today: date = None) -> List[Alert]:
        today = today or date.today()
        out = []
        month = today.strftime("%Y-%m")
        for cat, limit in self.budgets().items():
            spent = self.month_spend(cat, month)
            if spent >= limit:
                out.append(Alert("CRITICAL", f"{cat} budget exceeded: spent {spent:,.2f} of {limit:,.2f} this month."))
            elif spent >= limit * BUDGET_WARN_RATIO:
                out.append(Alert("WARNING", f"{cat} budget at {spent / limit:.0%}: {spent:,.2f} of {limit:,.2f}."))
        threshold = Decimal(self.settings["low_balance_threshold"])
        bal = self.balance()
        if bal < 0:
            out.append(Alert("CRITICAL", f"Balance is negative ({bal:,.2f})."))
        elif bal < threshold:
            out.append(Alert("WARNING", f"Balance {bal:,.2f} is below your limit of {threshold:,.2f}."))
        for t in self.anomalies()[:3]:
            out.append(Alert("WARNING", f"Unusual {t.category} expense on {t.date}: {t.amount:,.2f} (#{t.id})."))
        return out
