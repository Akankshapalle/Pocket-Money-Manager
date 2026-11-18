"""
Pocket Money Manager
A beginner-friendly terminal application for tracking money received and spent.
Python 3.10+. Core features use only the Python standard library.
"""

from __future__ import annotations

import csv
import json
import uuid
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
REPORT_DIR = APP_DIR / "reports"
CHART_DIR = APP_DIR / "charts"
DATA_FILE = DATA_DIR / "transactions.json"
BUDGET_FILE = DATA_DIR / "settings.json"

CATEGORIES = {
    "income": ["Allowance", "Gift", "Scholarship", "Part-time", "Other"],
    "expense": ["Food", "Travel", "Education", "Shopping", "Entertainment", "Savings", "Other"],
}
MAX_AMOUNT = 1_000_000.00
DEFAULT_MONTHLY_BUDGET = 3000.00
FIELDS = ["id", "date", "type", "amount", "category", "note"]


def ensure_folders() -> None:
    for folder in (DATA_DIR, REPORT_DIR, CHART_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def load_transactions() -> list[dict[str, Any]]:
    """Load and validate the local JSON file; recover safely from missing/corrupt files."""
    ensure_folders()
    if not DATA_FILE.exists():
        save_transactions([])
        return []
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("The data file must contain a JSON list.")
        valid = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                record = validate_record(item)
                valid.append(record)
            except (ValueError, TypeError, KeyError):
                # Ignore malformed rows rather than crashing the application.
                continue
        return valid
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        backup = DATA_FILE.with_name(f"transactions_corrupt_{datetime.now():%Y%m%d_%H%M%S}.json")
        try:
            DATA_FILE.replace(backup)
            print(f"\n[WARNING] Data file was unreadable. A backup was saved as {backup.name}.")
        except OSError:
            print(f"\n[WARNING] Could not read the data file: {exc}")
        save_transactions([])
        return []


def save_transactions(records: list[dict[str, Any]]) -> None:
    ensure_folders()
    temp_file = DATA_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(DATA_FILE)


def validate_record(item: dict[str, Any]) -> dict[str, Any]:
    tx_type = str(item["type"]).strip().lower()
    if tx_type not in ("income", "expense"):
        raise ValueError("Type must be income or expense.")
    amount = float(item["amount"])
    if not (0 < amount <= MAX_AMOUNT):
        raise ValueError("Amount is outside the allowed range.")
    tx_date = date.fromisoformat(str(item["date"]))
    category = str(item["category"]).strip()
    if not category or len(category) > 30:
        raise ValueError("Category is required and must be 30 characters or fewer.")
    note = str(item.get("note", "")).strip()[:120]
    tx_id = str(item.get("id") or uuid.uuid4().hex[:10])
    return {
        "id": tx_id,
        "date": tx_date.isoformat(),
        "type": tx_type,
        "amount": round(amount, 2),
        "category": category,
        "note": note,
    }


def read_nonempty(prompt: str, max_length: int = 30) -> str:
    while True:
        value = input(prompt).strip()
        if value and len(value) <= max_length:
            return value
        print(f"Please enter 1 to {max_length} characters.")


def read_amount() -> float:
    while True:
        raw = input(f"Amount (0.01 to {MAX_AMOUNT:,.2f}): ").strip().replace(",", "")
        try:
            amount = float(raw)
            if 0 < amount <= MAX_AMOUNT:
                return round(amount, 2)
            print("Amount must be greater than 0 and within the maximum limit.")
        except ValueError:
            print("Enter a valid number, for example 150 or 99.50.")


def read_date() -> str:
    while True:
        raw = input(f"Date (YYYY-MM-DD, Enter for {date.today()}): ").strip()
        if not raw:
            return date.today().isoformat()
        try:
            return date.fromisoformat(raw).isoformat()
        except ValueError:
            print("Invalid date. Use YYYY-MM-DD, for example 2026-11-18.")


def choose_category(tx_type: str) -> str:
    choices = CATEGORIES[tx_type]
    print("Categories: " + " | ".join(f"{i}. {name}" for i, name in enumerate(choices, 1)))
    while True:
        raw = input("Choose category number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        print(f"Choose a number from 1 to {len(choices)}.")


def add_transaction(records: list[dict[str, Any]], tx_type: str) -> None:
    print(f"\n--- Add {tx_type.title()} ---")
    amount = read_amount()
    category = choose_category(tx_type)
    note = input("Short note (optional, max 120 characters): ").strip()[:120]
    tx_date = read_date()
    record = validate_record({
        "id": uuid.uuid4().hex[:10], "date": tx_date, "type": tx_type,
        "amount": amount, "category": category, "note": note,
    })
    records.append(record)
    save_transactions(records)
    print(f"[SUCCESS] {tx_type.title()} of {money(amount)} saved. Current balance: {money(balance(records))}")
    check_budget(records)


def money(value: float) -> str:
    return f"₹{value:,.2f}"


def total(records: list[dict[str, Any]], tx_type: str) -> float:
    return round(sum(float(r["amount"]) for r in records if r["type"] == tx_type), 2)


def balance(records: list[dict[str, Any]]) -> float:
    return round(total(records, "income") - total(records, "expense"), 2)


def load_budget() -> float:
    ensure_folders()
    try:
        settings = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        value = float(settings.get("monthly_budget", DEFAULT_MONTHLY_BUDGET))
        return value if value > 0 else DEFAULT_MONTHLY_BUDGET
    except (OSError, ValueError, json.JSONDecodeError, AttributeError):
        save_budget(DEFAULT_MONTHLY_BUDGET)
        return DEFAULT_MONTHLY_BUDGET


def save_budget(value: float) -> None:
    ensure_folders()
    BUDGET_FILE.write_text(json.dumps({"monthly_budget": round(value, 2)}, indent=2), encoding="utf-8")


def check_budget(records: list[dict[str, Any]]) -> None:
    budget = load_budget()
    month = date.today().strftime("%Y-%m")
    spent = sum(float(r["amount"]) for r in records if r["type"] == "expense" and r["date"].startswith(month))
    if spent >= budget:
        print(f"[WARNING] This month's expenses ({money(spent)}) have reached/exceeded your budget ({money(budget)}).")
    elif spent >= budget * 0.8:
        print(f"[NOTICE] You have used {spent / budget:.0%} of this month's budget.")


def show_records(records: list[dict[str, Any]]) -> None:
    if not records:
        print("\nNo records found yet.")
        return
    ordered = sorted(records, key=lambda r: (r["date"], r["id"]), reverse=True)
    print("\n" + "-" * 100)
    print(f"{'DATE':<12} {'TYPE':<9} {'AMOUNT':>14}  {'CATEGORY':<18} {'NOTE':<30} {'ID':<10}")
    print("-" * 100)
    for r in ordered:
        print(f"{r['date']:<12} {r['type']:<9} {money(r['amount']):>14}  {r['category']:<18.18} {r['note']:<30.30} {r['id']:<10}")
    print("-" * 100)
    print(f"Showing {len(ordered)} record(s).")


def search_records(records: list[dict[str, Any]]) -> None:
    term = input("Search by keyword/category/type/date: ").strip().lower()
    if not term:
        print("Search cannot be blank.")
        return
    matches = [r for r in records if term in " ".join(str(r[k]) for k in FIELDS).lower()]
    show_records(matches)


def show_summary(records: list[dict[str, Any]]) -> None:
    income, expenses = total(records, "income"), total(records, "expense")
    count = len(records)
    expense_rows = [r for r in records if r["type"] == "expense"]
    average = sum(r["amount"] for r in expense_rows) / len(expense_rows) if expense_rows else 0
    category_totals: dict[str, float] = defaultdict(float)
    for r in expense_rows:
        category_totals[r["category"]] += float(r["amount"])
    print("\n========== POCKET MONEY SUMMARY ==========")
    print(f"Total money received : {money(income)}")
    print(f"Total money spent    : {money(expenses)}")
    print(f"Current balance      : {money(balance(records))}")
    print(f"Total records        : {count}")
    print(f"Average expense      : {money(average)}")
    print(f"Monthly budget       : {money(load_budget())}")
    print(f"Budget status        : {'OVER BUDGET' if current_month_spend(records) > load_budget() else 'WITHIN BUDGET'}")
    if category_totals:
        print("\nExpenses by category:")
        for category, amount in sorted(category_totals.items(), key=lambda pair: pair[1], reverse=True):
            print(f"  {category:<18} {money(amount)}")
    else:
        print("\nNo expenses recorded yet.")
    print("==========================================")
    check_budget(records)


def current_month_spend(records: list[dict[str, Any]]) -> float:
    month = date.today().strftime("%Y-%m")
    return sum(float(r["amount"]) for r in records if r["type"] == "expense" and r["date"].startswith(month))


def export_csv(records: list[dict[str, Any]]) -> Path:
    ensure_folders()
    path = REPORT_DIR / f"pocket_money_report_{date.today().isoformat()}.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(records, key=lambda r: r["date"]))
    return path


def export_text_report(records: list[dict[str, Any]]) -> Path:
    ensure_folders()
    path = REPORT_DIR / f"pocket_money_summary_{date.today().isoformat()}.md"
    income, expenses = total(records, "income"), total(records, "expense")
    lines = [
        "# Pocket Money Manager Report", "",
        f"- Generated: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Total received: {money(income)}",
        f"- Total spent: {money(expenses)}",
        f"- Current balance: {money(balance(records))}",
        f"- Number of records: {len(records)}",
        f"- Average expense: {money(expenses / max(1, sum(r['type'] == 'expense' for r in records)))}",
        "", "## Transaction Log", "",
        "| Date | Type | Amount | Category | Note |",
        "|---|---|---:|---|---|",
    ]
    for r in sorted(records, key=lambda x: x["date"]):
        note = r["note"].replace("|", "/")
        lines.append(f"| {r['date']} | {r['type']} | {money(r['amount'])} | {r['category']} | {note} |")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def import_csv(records: list[dict[str, Any]]) -> None:
    raw_path = input("CSV file path (or drag the file into this terminal): ").strip().strip('"')
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        print("File not found. No data was changed.")
        return
    added, errors = 0, []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            missing = set(FIELDS) - set(reader.fieldnames or [])
            if missing:
                print("CSV is missing columns: " + ", ".join(sorted(missing)))
                return
            existing_ids = {r["id"] for r in records}
            for line_no, row in enumerate(reader, start=2):
                try:
                    item = validate_record(row)
                    if item["id"] in existing_ids:
                        item["id"] = uuid.uuid4().hex[:10]
                    records.append(item)
                    existing_ids.add(item["id"])
                    added += 1
                except (ValueError, TypeError, KeyError) as exc:
                    errors.append(f"Row {line_no}: {exc}")
        save_transactions(records)
        print(f"Imported {added} valid row(s).")
        if errors:
            print(f"Skipped {len(errors)} invalid row(s):")
            for message in errors[:10]:
                print(" - " + message)
            if len(errors) > 10:
                print(f" - ...and {len(errors) - 10} more.")
    except OSError as exc:
        print(f"Could not read CSV: {exc}")


def create_charts(records: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib is not installed. Run: pip install -r requirements.txt")
        return
    if not records:
        print("Add or import some records before creating charts.")
        return

    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    categories: dict[str, float] = defaultdict(float)
    for r in records:
        month = r["date"][:7]
        monthly[month][r["type"]] += float(r["amount"])
        if r["type"] == "expense":
            categories[r["category"]] += float(r["amount"])

    months = sorted(monthly)
    plt.figure(figsize=(9, 5))
    plt.plot(months, [monthly[m]["income"] for m in months], marker="o", label="Received")
    plt.plot(months, [monthly[m]["expense"] for m in months], marker="o", label="Spent")
    plt.title("Monthly Money Trend")
    plt.xlabel("Month")
    plt.ylabel("Amount (INR)")
    plt.xticks(rotation=30, ha="right")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    trend_path = CHART_DIR / "monthly_trend.png"
    plt.savefig(trend_path, dpi=150)
    plt.close()

    if categories:
        plt.figure(figsize=(8, 5))
        plt.bar(categories.keys(), categories.values())
        plt.title("Expenses by Category")
        plt.xlabel("Category")
        plt.ylabel("Amount (INR)")
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        category_path = CHART_DIR / "expense_categories.png"
        plt.savefig(category_path, dpi=150)
        plt.close()
        print(f"Charts saved to:\n- {trend_path}\n- {category_path}")
    else:
        print(f"Trend chart saved to: {trend_path}")


def set_budget() -> None:
    while True:
        raw = input("Enter monthly spending budget in ₹: ").strip().replace(",", "")
        try:
            value = float(raw)
            if 0 < value <= MAX_AMOUNT:
                save_budget(value)
                print(f"Monthly budget updated to {money(value)}.")
                return
            print("Budget must be greater than zero and within the maximum limit.")
        except ValueError:
            print("Enter a valid numeric amount.")


def print_banner() -> None:
    print("\n" + "=" * 54)
    print("          POCKET MONEY MANAGER")
    print("       Track smart. Spend mindfully.")
    print("=" * 54)


def main() -> None:
    ensure_folders()
    records = load_transactions()
    print_banner()
    print(f"Loaded {len(records)} saved record(s). Current balance: {money(balance(records))}")
    while True:
        print("""
  1. Add money received
  2. Add money spent
  3. View all records
  4. Search records
  5. View summary
  6. Generate charts
  7. Export reports (CSV + Markdown)
  8. Import records from CSV
  9. Set monthly spending budget
  0. Save and exit
""")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            add_transaction(records, "income")
        elif choice == "2":
            add_transaction(records, "expense")
        elif choice == "3":
            show_records(records)
        elif choice == "4":
            search_records(records)
        elif choice == "5":
            show_summary(records)
        elif choice == "6":
            create_charts(records)
        elif choice == "7":
            print(f"CSV report saved: {export_csv(records)}")
            print(f"Markdown report saved: {export_text_report(records)}")
        elif choice == "8":
            import_csv(records)
        elif choice == "9":
            set_budget()
        elif choice == "0":
            save_transactions(records)
            print(f"Data saved. Final balance: {money(balance(records))}")
            print("Thank you for using Pocket Money Manager!")
            break
        else:
            print("Invalid option. Please choose a number from 0 to 9.")


if __name__ == "__main__":
    main()
