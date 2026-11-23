"""Core data structures."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

INCOME = "income"
EXPENSE = "expense"
KINDS = (INCOME, EXPENSE)


@dataclass(frozen=True)
class Transaction:
    """One pocket-money entry. Amounts use Decimal so money never drifts."""
    id: int
    date: date
    kind: str
    category: str
    amount: Decimal
    note: str = ""

    @property
    def month(self) -> str:
        return self.date.strftime("%Y-%m")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "kind": self.kind,
            "category": self.category,
            "amount": str(self.amount),
            "note": self.note,
        }


@dataclass(frozen=True)
class Alert:
    level: str      # "WARNING" or "CRITICAL"
    message: str
