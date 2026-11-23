"""Matplotlib charts. Degrades gracefully if matplotlib is not installed."""
from pathlib import Path
from typing import List


class ChartsUnavailable(RuntimeError):
    pass


def generate_charts(ledger, outdir) -> List[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")                       # render to files; no display needed
        import matplotlib.pyplot as plt
    except ImportError:
        raise ChartsUnavailable("matplotlib is not installed. Run: pip install matplotlib") from None
    if len(ledger) == 0:
        raise ChartsUnavailable("No entries yet - add some before generating charts.")

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    made = []

    monthly = ledger.monthly_totals()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    months = [m for m, _, _ in monthly]
    x = range(len(months))
    ax.bar([i - 0.2 for i in x], [float(i) for _, i, _ in monthly], 0.4, label="Received", color="#2e9e5b")
    ax.bar([i + 0.2 for i in x], [float(e) for _, _, e in monthly], 0.4, label="Spent", color="#d9534f")
    ax.set_xticks(list(x))
    ax.set_xticklabels(months)
    ax.set_title("Monthly received vs spent")
    ax.set_ylabel("Amount (Rs.)")
    ax.legend()
    made.append(_save(fig, plt, outdir / "monthly_income_vs_expense.png"))

    cats = ledger.category_totals()
    if cats:
        fig, ax = plt.subplots(figsize=(6.5, 6.5))
        ax.pie([float(v) for v in cats.values()], labels=list(cats), autopct="%1.0f%%", startangle=90)
        ax.set_title("Spending by category")
        made.append(_save(fig, plt, outdir / "spending_by_category.png"))

    history = ledger.balance_history()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot([d for d, _ in history], [float(b) for _, b in history], marker="o", color="#2b6cb0")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_title("Balance trend")
    ax.set_ylabel("Balance (Rs.)")
    fig.autofmt_xdate()
    made.append(_save(fig, plt, outdir / "balance_trend.png"))
    return made


def _save(fig, plt, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
