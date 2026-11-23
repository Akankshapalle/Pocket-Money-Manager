"""Summary metrics and text rendering."""
import calendar
from datetime import date
from decimal import Decimal

from .formatting import money, table
from .ledger import Ledger
from .models import EXPENSE, INCOME

ZERO = Decimal("0.00")


def build_summary(ledger: Ledger, today: date = None) -> dict:
    today = today or date.today()
    txs = ledger.all()
    incomes = [t for t in txs if t.kind == INCOME]
    expenses = [t for t in txs if t.kind == EXPENSE]
    total_in, total_out = ledger.total(INCOME), ledger.total(EXPENSE)
    balance = total_in - total_out
    cats = ledger.category_totals(EXPENSE)
    monthly = ledger.monthly_totals()

    savings_rate = float((balance / total_in) * 100) if total_in > 0 else None
    this_month = today.strftime("%Y-%m")
    spent_so_far = next((e for m, _, e in monthly if m == this_month), ZERO)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    forecast = (spent_so_far / today.day * days_in_month).quantize(Decimal("0.01")) if spent_so_far else ZERO

    trend = None
    if len(monthly) >= 2 and monthly[-2][2] > 0:
        prev, cur = monthly[-2], monthly[-1]
        change = float((cur[2] - prev[2]) / prev[2] * 100)
        trend = f"Spending {'up' if change >= 0 else 'down'} {abs(change):.1f}% in {cur[0]} vs {prev[0]}"

    threshold = Decimal(ledger.settings["low_balance_threshold"])
    if balance < 0:
        status = "CRITICAL"
    elif balance < threshold or any(a.level == "CRITICAL" for a in ledger.alerts(today)):
        status = "CAUTION"
    else:
        status = "HEALTHY"

    return {
        "generated": today.isoformat(),
        "entries": len(txs),
        "total_income": total_in, "total_expense": total_out, "balance": balance,
        "avg_income": (total_in / len(incomes)).quantize(Decimal("0.01")) if incomes else ZERO,
        "avg_expense": (total_out / len(expenses)).quantize(Decimal("0.01")) if expenses else ZERO,
        "largest_expense": max(expenses, key=lambda t: t.amount) if expenses else None,
        "top_category": next(iter(cats.items()), None),
        "categories": cats, "monthly": monthly,
        "savings_rate": savings_rate, "forecast_month_spend": forecast,
        "trend": trend, "status": status,
    }


def render_text(s: dict, alerts=()) -> str:
    rate = "n/a" if s["savings_rate"] is None else "%.1f%%" % s["savings_rate"]
    lines = [f"EXECUTIVE SUMMARY  (generated {s['generated']})", "=" * 60,
             f"Entries recorded : {s['entries']}",
             f"Total received   : {money(s['total_income'])}",
             f"Total spent      : {money(s['total_expense'])}",
             f"Current balance  : {money(s['balance'])}",
             f"Average received : {money(s['avg_income'])}",
             f"Average expense  : {money(s['avg_expense'])}",
             f"Savings rate     : {rate}",
             f"Status           : {s['status']}"]
    if s["largest_expense"]:
        t = s["largest_expense"]
        lines.append(f"Largest expense  : {money(t.amount)} ({t.category}, {t.date})")
    if s["top_category"]:
        lines.append(f"Top category     : {s['top_category'][0]} ({money(s['top_category'][1])})")
    if s["forecast_month_spend"]:
        lines.append(f"Month-end forecast spend: {money(s['forecast_month_spend'])}")
    if s["trend"]:
        lines.append(f"Trend            : {s['trend']}")
    if s["monthly"]:
        lines += ["", "Monthly overview", table(
            ["Month", "Received", "Spent", "Net"],
            [(m, f"{i:,.2f}", f"{e:,.2f}", f"{i - e:,.2f}") for m, i, e in s["monthly"]],
            right_align=(1, 2, 3))]
    if s["categories"]:
        total = s["total_expense"] or Decimal(1)
        lines += ["", "Spending by category", table(
            ["Category", "Spent", "Share"],
            [(c, f"{a:,.2f}", f"{a / total:.1%}") for c, a in s["categories"].items()],
            right_align=(1, 2))]
    if alerts:
        lines += ["", "Warnings"] + [f"  [{a.level}] {a.message}" for a in alerts]
    return "\n".join(lines)
