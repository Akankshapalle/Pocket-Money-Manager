"""Export reports as CSV, Markdown and plain-text audit logs."""
import csv
from datetime import datetime
from pathlib import Path

from .formatting import money
from .reports import render_text

_FORMULA_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection (a note like '=cmd|...')."""
    return "'" + value if value and value.startswith(_FORMULA_CHARS) else value


def _prepare(path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_csv(ledger, path) -> Path:
    path = _prepare(path)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "date", "type", "category", "amount", "note"])
        for t in ledger.all():
            w.writerow([t.id, t.date.isoformat(), t.kind, _safe_cell(t.category), t.amount, _safe_cell(t.note)])
    return path


def export_markdown(summary, ledger, path, alerts=()) -> Path:
    path = _prepare(path)
    md = [f"# Pocket Money Report - {summary['generated']}", "",
          "| Metric | Value |", "|---|---|",
          f"| Received | {money(summary['total_income'])} |",
          f"| Spent | {money(summary['total_expense'])} |",
          f"| Balance | {money(summary['balance'])} |",
          f"| Status | {summary['status']} |", "",
          "## Monthly overview", "", "| Month | Received | Spent | Net |", "|---|---:|---:|---:|"]
    md += [f"| {m} | {i:,.2f} | {e:,.2f} | {i - e:,.2f} |" for m, i, e in summary["monthly"]]
    md += ["", "## Spending by category", "", "| Category | Spent |", "|---|---:|"]
    md += [f"| {c} | {a:,.2f} |" for c, a in summary["categories"].items()]
    if alerts:
        md += ["", "## Warnings", ""] + [f"- **{a.level}**: {a.message}" for a in alerts]
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return path


def export_audit_log(summary, ledger, path, alerts=()) -> Path:
    path = _prepare(path)
    lines = [f"AUDIT LOG - exported {datetime.now():%Y-%m-%d %H:%M:%S}", "",
             render_text(summary, alerts), "", "ALL ENTRIES (oldest first)", "-" * 60]
    lines += [f"#{t.id:<4} {t.date}  {t.kind:<7} {t.category:<18} {t.amount:>12,.2f}  {t.note}"
              for t in ledger.all()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
