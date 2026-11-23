"""Terminal formatting helpers: money, tables, colours, pagination."""
import math
import os
import sys
from decimal import Decimal

CURRENCY = "Rs."
COLORS = {"red": "31", "green": "32", "yellow": "33", "blue": "34", "cyan": "36", "bold": "1", "dim": "2"}


def use_color() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def paint(text: str, color: str, enabled: bool = None) -> str:
    enabled = use_color() if enabled is None else enabled
    return f"\033[{COLORS[color]}m{text}\033[0m" if enabled else text


def money(value) -> str:
    return f"{CURRENCY} {Decimal(value):,.2f}"


def table(headers, rows, right_align=()):
    """Plain-text table with fixed-width columns. right_align holds column indexes."""
    rows = [[str(c) for c in r] for r in rows]
    widths = [max(len(str(h)), *(len(r[i]) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def fmt(cells):
        parts = [(c.rjust(w) if i in right_align else c.ljust(w))
                 for i, (c, w) in enumerate(zip(cells, widths))]
        return "| " + " | ".join(parts) + " |"

    out = [line, fmt([str(h) for h in headers]), line]
    out += [fmt(r) for r in rows]
    out.append(line)
    return "\n".join(out)


def paginate(items, page: int, size: int):
    """Return (slice, clamped page, total pages) for 1-based page numbers."""
    pages = max(1, math.ceil(len(items) / size))
    page = min(max(1, page), pages)
    return items[(page - 1) * size: page * size], page, pages


def transactions_table(txs):
    rows = [(t.id, t.date.isoformat(), t.kind, t.category,
             ("+" if t.kind == "income" else "-") + f"{t.amount:,.2f}", t.note[:30]) for t in txs]
    return table(["ID", "Date", "Type", "Category", "Amount", "Note"], rows, right_align=(0, 4))
