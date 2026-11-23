"""Centralised input validation. Every entry point (CLI, import, storage) uses these."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .models import EXPENSE, INCOME

MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000.00")
MIN_DATE = date(2000, 1, 1)
MAX_NOTE_LEN = 100
_CATEGORY_RE = re.compile(r"^[A-Za-z][A-Za-z &/\-]{0,29}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
_KIND_ALIASES = {
    "income": INCOME, "in": INCOME, "i": INCOME, "received": INCOME, "credit": INCOME,
    "expense": EXPENSE, "ex": EXPENSE, "e": EXPENSE, "spent": EXPENSE, "debit": EXPENSE,
}


class ValidationError(ValueError):
    """Raised with a human-friendly message when input is not acceptable."""


def parse_amount(value) -> Decimal:
    text = str(value).strip().replace(",", "")
    text = re.sub(r"^(rs\.?|inr|\u20b9)\s*", "", text, flags=re.IGNORECASE)
    if not text:
        raise ValidationError("Amount cannot be blank.")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"'{value}' is not a valid number.") from None
    if not amount.is_finite():
        raise ValidationError("Amount must be a finite number.")
    if amount.as_tuple().exponent < -2:
        raise ValidationError("Amount can have at most 2 decimal places.")
    if amount < MIN_AMOUNT:
        raise ValidationError(f"Amount must be at least {MIN_AMOUNT}.")
    if amount > MAX_AMOUNT:
        raise ValidationError(f"Amount cannot exceed {MAX_AMOUNT:,}.")
    return amount.quantize(Decimal("0.01"))


def parse_date(value, today: date = None) -> date:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            raise ValidationError("Date cannot be blank.")
        parsed = None
        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValidationError("Use a date like 2026-11-23 or 23-11-2026.")
    today = today or date.today()
    if parsed > today:
        raise ValidationError("Date cannot be in the future.")
    if parsed < MIN_DATE:
        raise ValidationError(f"Date cannot be before {MIN_DATE.isoformat()}.")
    return parsed


def parse_kind(value) -> str:
    key = str(value).strip().lower()
    if key not in _KIND_ALIASES:
        raise ValidationError("Type must be 'income' (i) or 'expense' (e).")
    return _KIND_ALIASES[key]


def parse_category(value) -> str:
    text = " ".join(str(value).split())
    if not _CATEGORY_RE.match(text):
        raise ValidationError(
            "Category must start with a letter, use letters/spaces/&/-, max 30 characters.")
    return text.title()


def parse_note(value) -> str:
    text = " ".join(_CONTROL_RE.sub(" ", str(value or "")).split())
    if len(text) > MAX_NOTE_LEN:
        raise ValidationError(f"Note is too long (max {MAX_NOTE_LEN} characters).")
    return text


def parse_day_of_month(value) -> int:
    try:
        day = int(str(value).strip())
    except ValueError:
        raise ValidationError("Day must be a whole number between 1 and 31.") from None
    if not 1 <= day <= 31:
        raise ValidationError("Day must be between 1 and 31.")
    return day


def parse_page_choice(value) -> str:
    key = str(value).strip().lower()
    if key not in {"n", "p", "q", ""}:
        raise ValidationError("Enter n (next), p (previous) or q (quit).")
    return key or "n"


def validate_record(raw: dict, today: date = None) -> dict:
    """Validate a dict with date/kind/category/amount/note; return cleaned typed values."""
    missing = [k for k in ("date", "kind", "category", "amount") if k not in raw]
    if missing:
        raise ValidationError("Missing field(s): " + ", ".join(missing))
    return {
        "date": parse_date(raw["date"], today),
        "kind": parse_kind(raw["kind"]),
        "category": parse_category(raw["category"]),
        "amount": parse_amount(raw["amount"]),
        "note": parse_note(raw.get("note", "")),
    }
