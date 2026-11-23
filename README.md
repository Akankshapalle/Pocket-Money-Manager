# Pocket Money Manager

A menu-driven Python terminal app to log pocket money **received** and **spent**, check balances,
search records, see summaries and warnings, draw Matplotlib charts, and export reports.
Built for the DataSpark Challenge (Project #14). Needs Python 3.10+.

## Run it
```
pip install -r requirements.txt     # only needed for charts
python main.py --demo               # first run: loads 41 sample entries
python main.py                      # normal use (data kept in data/pocket_money.json)
python -m unittest discover -s tests   # run the 39 automated tests
```
Options: `--data FILE` (use another JSON file), `--reports FOLDER` (where exports/charts go).

## Features
| Requirement | Where |
|---|---|
| Menu-driven terminal UI, ANSI colour, paged tables | `cli.py`, `formatting.py` |
| Defensive validation (amount, date, type, category, note) | `validation.py` |
| Log received/spent, balances, budgets | `ledger.py` |
| JSON persistence, atomic saves, corrupted-file recovery | `storage.py` |
| Search by keyword, category, type, date range | `Ledger.search` (category index) |
| Executive summary: totals, averages, savings rate, trend, month-end forecast, status | `reports.py` |
| Matplotlib charts (monthly bars, category pie, balance trend) | `charts.py` |
| Export CSV / Markdown / text audit log | `exporters.py` |
| Warnings: budget limits, low balance, unusual expenses | `Ledger.alerts` |
| Bulk CSV import with row-by-row error log | `importer.py` |
| Monthly recurring allowance/bills (catch-up, no duplicates) | `Ledger.apply_recurring` |

## Design notes
- **Modular layers**: models -> validation -> ledger (logic) -> storage / reports / exporters / charts / importer -> cli.
  Logic has no `print` or `input`, so it is fully unit-testable.
- **Decimal money**: no floating-point drift (0.10 x 10 is exactly 1.00).
- **Indexes**: the ledger keeps category and month indexes, so filtered searches and monthly totals avoid full scans; lists are paginated.
- **Safe saves**: data is written to a temp file, then swapped in with `os.replace`, so a crash cannot corrupt the file.
  An unreadable file is renamed `*.corrupt-<time>.json` and the app starts clean instead of crashing.
- **Security**: strict input limits, control characters stripped, CSV formula-injection guard on export, import size/row caps.
- **Anomaly rule**: an expense above 2.5x its category median (needs 5+ entries) is flagged.

## Demo script (about 3 minutes)
1. `python main.py --demo`, point out the banner and warnings.
2. Option 1: type a bad type (`x`), a bad date (`31-02-2026`), a bad amount (`abc`, `-4`) and show each is rejected, then enter valid values.
3. Option 4: summary tables. Option 5: charts saved in `reports/charts/`.
4. Option 8: import `data/legacy_with_errors.csv`, show the row-by-row error log.
5. Option 7: exports. Exit, relaunch `python main.py` and show the data is still there.

## Sample data (`data/`)
`sample_transactions.csv` / `.json` (41 entries incl. boundary 0.01 and an outlier), `legacy_with_errors.csv` (9 rows, 7 deliberately bad).
Regenerate with `python scripts/make_sample_data.py`.
