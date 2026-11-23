"""Menu-driven terminal interface."""
import argparse
import webbrowser
from datetime import date
from pathlib import Path

from . import __version__
from .charts import ChartsUnavailable, generate_charts
from .exporters import export_audit_log, export_csv, export_markdown
from .formatting import money, paginate, paint, transactions_table, use_color
from .importer import ImportFailure, import_csv, write_error_log
from .reports import build_summary, render_text
from .storage import Storage
from .validation import (ValidationError, parse_amount, parse_category, parse_date,
                         parse_day_of_month, parse_kind, parse_note, parse_page_choice)

ROOT = Path(__file__).resolve().parent.parent
PAGE_SIZE = 10
BANNER = r"""
  ____            _        _     __  __
 |  _ \ ___   ___| | _____| |_  |  \/  | ___  _ __   ___ _   _
 | |_) / _ \ / __| |/ / _ \ __| | |\/| |/ _ \| '_ \ / _ \ | | |
 |  __/ (_) | (__|   <  __/ |_  | |  | | (_) | | | |  __/ |_| |
 |_|   \___/ \___|_|\_\___|\__| |_|  |_|\___/|_| |_|\___|\__, |
                                                         |___/
            M A N A G E R   -   track every rupee
"""
MENU = """
 1. Add entry (received / spent)     6. Budgets, limits & recurring
 2. View all entries (paged)         7. Export reports
 3. Search & filter                  8. Import CSV
 4. Summary & warnings               9. Delete an entry
 5. Charts (Matplotlib)              0. Exit
"""


def ask(prompt, parser, default=None):
    """Keep asking until the parser accepts the answer."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw == "" and default is not None:
            raw = str(default)
        try:
            return parser(raw)
        except ValidationError as exc:
            print(paint(f"  [!] {exc}", "red"))


def ask_optional(prompt, parser):
    """Blank answer returns None."""
    while True:
        raw = input(f"{prompt} (blank to skip): ").strip()
        if not raw:
            return None
        try:
            return parser(raw)
        except ValidationError as exc:
            print(paint(f"  [!] {exc}", "red"))


def ask_yes(prompt) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


class App:
    def __init__(self, storage: Storage, ledger, reports_dir: Path):
        self.storage, self.ledger, self.reports_dir = storage, ledger, Path(reports_dir)
        self.handlers = {"1": self.add_entry, "2": self.view_all, "3": self.search,
                         "4": self.summary, "5": self.charts, "6": self.settings_menu,
                         "7": self.export, "8": self.import_file, "9": self.delete_entry}

    def save(self):
        self.storage.save(self.ledger)

    def run(self):
        print(paint(BANNER, "cyan"))
        print(f"  Version {__version__}   |   Balance: {money(self.ledger.balance())}")
        self.show_alerts()
        while True:
            print(MENU)
            choice = input("Choose an option: ").strip()
            if choice == "0":
                self.save()
                print("Saved. Goodbye!")
                return
            handler = self.handlers.get(choice)
            if handler is None:
                print(paint("  [!] Please enter a number from the menu.", "red"))
                continue
            try:
                handler()
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")

    def show_alerts(self):
        for a in self.ledger.alerts(date.today()):
            print(paint(f"  [{a.level}] {a.message}", "red" if a.level == "CRITICAL" else "yellow"))

    # ---------- handlers ----------
    def add_entry(self):
        print("\n-- Add entry --")
        kind = ask("Type: (i)ncome / (e)xpense", parse_kind)
        when = ask("Date (YYYY-MM-DD)", parse_date, default=date.today().isoformat())
        if self.ledger.categories():
            print("  Existing categories: " + ", ".join(self.ledger.categories()))
        category = ask("Category", parse_category)
        amount = ask("Amount", parse_amount)
        note = ask("Note (optional)", parse_note, default="")
        t = self.ledger.add(when, kind, category, amount, note)
        self.save()
        print(paint(f"  Saved entry #{t.id}. New balance: {money(self.ledger.balance())}", "green"))
        self.show_alerts()

    def _paged(self, txs, title):
        if not txs:
            print("  No matching entries.")
            return
        page = 1
        while True:
            chunk, page, pages = paginate(txs, page, PAGE_SIZE)
            print(f"\n{title} - page {page}/{pages} ({len(txs)} entries)")
            print(transactions_table(chunk))
            if pages == 1:
                return
            choice = ask("[n]ext / [p]revious / [q]uit", parse_page_choice, default="n")
            if choice == "q":
                return
            page += 1 if choice == "n" else -1
            if page > pages:
                return

    def view_all(self):
        self._paged(list(reversed(self.ledger.all())), "All entries (newest first)")

    def search(self):
        print("\n-- Search (leave a filter blank to skip it) --")
        keyword = input("Keyword in category/note (blank to skip): ").strip() or None
        category = ask_optional("Category", parse_category)
        kind = ask_optional("Type (i/e)", parse_kind)
        start = ask_optional("From date", parse_date)
        end = ask_optional("To date", parse_date)
        results = self.ledger.search(keyword, category, kind, start, end)
        self._paged(results, "Search results")
        if results:
            ins = self.ledger.total("income", results)
            outs = self.ledger.total("expense", results)
            print(f"  Matches: received {money(ins)}, spent {money(outs)}")

    def summary(self):
        alerts = self.ledger.alerts(date.today())
        print("\n" + render_text(build_summary(self.ledger), alerts))

    def charts(self):
        try:
            paths = generate_charts(self.ledger, self.reports_dir / "charts")
        except ChartsUnavailable as exc:
            print(paint(f"  [!] {exc}", "yellow"))
            return
        for p in paths:
            print(f"  Saved {p}")
        if ask_yes("Open the first chart now?"):
            webbrowser.open(paths[0].resolve().as_uri())

    def settings_menu(self):
        print("\n-- Budgets, limits & recurring --")
        print(" a) Set monthly budget for a category    b) Remove a budget")
        print(" c) Set low-balance warning limit        d) Add monthly allowance/bill")
        print(" e) Show current settings")
        choice = input("Choose: ").strip().lower()
        if choice == "a":
            self.ledger.set_budget(ask("Category", parse_category), ask("Monthly budget", parse_amount))
        elif choice == "b":
            self.ledger.remove_budget(ask("Category", parse_category))
        elif choice == "c":
            self.ledger.set_low_balance_threshold(ask("Warn when balance below", parse_amount))
        elif choice == "d":
            kind = ask("Type: (i)ncome / (e)xpense", parse_kind)
            category = ask("Category", parse_category)
            amount = ask("Amount", parse_amount)
            day = ask("Day of month (1-31)", parse_day_of_month)
            self.ledger.add_recurring(kind, category, amount, day)
            created = self.ledger.apply_recurring()
            print(f"  Recurring rule added; {len(created)} entr{'y' if len(created) == 1 else 'ies'} created now.")
        elif choice == "e":
            budgets = self.ledger.budgets()
            print("  Budgets: " + (", ".join(f"{c} {money(a)}" for c, a in budgets.items()) or "none"))
            print(f"  Low-balance limit: {money(self.ledger.settings['low_balance_threshold'])}")
            print(f"  Recurring rules: {len(self.ledger.settings['recurring'])}")
            return
        else:
            print(paint("  [!] Unknown option.", "red"))
            return
        self.save()
        print(paint("  Settings saved.", "green"))

    def export(self):
        summary = build_summary(self.ledger)
        alerts = self.ledger.alerts(date.today())
        stamp = date.today().strftime("%Y%m%d")
        paths = [export_csv(self.ledger, self.reports_dir / f"entries_{stamp}.csv"),
                 export_markdown(summary, self.ledger, self.reports_dir / f"summary_{stamp}.md", alerts),
                 export_audit_log(summary, self.ledger, self.reports_dir / f"audit_{stamp}.txt", alerts)]
        for p in paths:
            print(f"  Wrote {p}")

    def import_file(self):
        raw = input("Path to CSV file (columns: date,type,category,amount,note): ").strip().strip('"')
        if not raw:
            return
        try:
            result = import_csv(raw, self.ledger)
        except ImportFailure as exc:
            print(paint(f"  [!] {exc}", "red"))
            return
        self.save()
        print(f"  Imported {result.imported}, skipped {result.skipped}.")
        if result.errors:
            log = write_error_log(result, raw, self.reports_dir / "import_errors.log")
            for n, msg in result.errors[:5]:
                print(f"    Row {n}: {msg}")
            print(f"  Full row-by-row log: {log}")

    def delete_entry(self):
        def parse_id(text):
            try:
                return int(text)
            except ValueError:
                raise ValidationError("Enter the numeric ID shown in the table.") from None
        tid = ask("ID to delete", parse_id)
        t = self.ledger.get(tid)
        if t is None:
            print(paint(f"  [!] No entry with id {tid}.", "red"))
            return
        print(transactions_table([t]))
        if ask_yes("Delete this entry?"):
            self.ledger.delete(tid)
            self.save()
            print("  Deleted.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pocket Money Manager")
    parser.add_argument("--data", default=str(ROOT / "data" / "pocket_money.json"), help="data file (JSON)")
    parser.add_argument("--reports", default=str(ROOT / "reports"), help="folder for exports and charts")
    parser.add_argument("--demo", action="store_true", help="load sample data if the ledger is empty")
    args = parser.parse_args(argv)

    storage = Storage(args.data)
    ledger, warnings = storage.load()
    for w in warnings:
        print(paint(f"[notice] {w}", "yellow"))
    if args.demo and len(ledger) == 0:
        sample = ROOT / "data" / "sample_transactions.csv"
        try:
            res = import_csv(sample, ledger)
            print(f"[demo] Loaded {res.imported} sample entries.")
        except ImportFailure as exc:
            print(paint(f"[demo] Could not load sample data: {exc}", "yellow"))
    created = ledger.apply_recurring()
    if created or args.demo:
        storage.save(ledger)
    App(storage, ledger, args.reports).run()
