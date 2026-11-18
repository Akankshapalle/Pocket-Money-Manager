# Pocket Money Manager

A beginner-friendly Python terminal application for recording pocket money received and spent.

## Features

- Menu-driven terminal interface
- Add income and expenses with validation
- Automatic balance calculation
- JSON local storage (records survive restart)
- Search by keyword, category, type, date, or note
- Summary: totals, balance, average expense, category totals
- Monthly spending budget with 80% and 100% warning messages
- CSV and Markdown report export
- CSV bulk import with row-by-row validation feedback
- Matplotlib charts: monthly trend and expense categories
- Safe handling of missing/corrupted JSON files

## Requirements

- Python 3.10 or newer
- Matplotlib is optional (only needed for charts)

## Run in VS Code

1. Extract `Pocket_Money_Manager.zip`.
2. Open VS Code.
3. Select **File → Open Folder** and choose the `Pocket_Money_Manager` folder.
4. Open **Terminal → New Terminal**.
5. (Optional but recommended) Create a virtual environment:

   Windows:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

   macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

6. Install chart support:
   ```bash
   python -m pip install -r requirements.txt
   ```
   If you do not need charts, you can skip this step.
7. Run:
   ```bash
   python main.py
   ```
   On some Windows systems, use `py main.py`.

## Menu

| Option | Action |
|---|---|
| 1 | Add money received |
| 2 | Add money spent |
| 3 | View all records |
| 4 | Search records |
| 5 | View summary |
| 6 | Generate charts |
| 7 | Export CSV and Markdown reports |
| 8 | Import a CSV file |
| 9 | Set monthly spending budget |
| 0 | Save and exit |

## Project structure

```text
Pocket_Money_Manager/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   ├── transactions.json
│   └── settings.json
├── sample_data/
│   └── sample_transactions.csv
├── reports/
└── charts/
```

- `data/transactions.json` is the app's live database.
- `sample_data/sample_transactions.csv` contains 40 demo rows. Use menu option 8 to import it.
- Reports and charts are created in their respective folders.

## Demo flow for your hackathon

1. Start the app with `python main.py`.
2. Choose option 1 and add income.
3. Choose option 2 and try invalid values such as blank text or `abc`; the app asks again instead of crashing.
4. Choose option 5 to show the balance and summary.
5. Choose option 6 to create charts (requires Matplotlib).
6. Choose option 7 to export reports.
7. Exit with option 0 and run the app again to demonstrate saved data.

## Data format

Each transaction has:
- `id`: unique record identifier
- `date`: date in `YYYY-MM-DD` format
- `type`: `income` or `expense`
- `amount`: positive numeric amount in INR
- `category`: transaction category
- `note`: optional description

## Notes

- The app works offline and does not require an API key or internet connection.
- The default monthly spending budget is ₹3,000; change it using menu option 9.
- Keep a backup of the `data` folder if you want to preserve your records.
