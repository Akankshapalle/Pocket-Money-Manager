"""Bulk CSV import with row-by-row validation and an error log."""
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .validation import ValidationError, validate_record

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
_ALIASES = {"type": "kind", "kind": "kind", "date": "date", "category": "category",
            "amount": "amount", "note": "note", "description": "note"}
_REQUIRED = {"date", "kind", "category", "amount"}


class ImportFailure(Exception):
    """The file as a whole cannot be imported."""


@dataclass
class ImportResult:
    imported: int = 0
    errors: List[Tuple[int, str]] = field(default_factory=list)

    @property
    def skipped(self) -> int:
        return len(self.errors)


def import_csv(path, ledger) -> ImportResult:
    path = Path(path).expanduser()
    if not path.is_file():
        raise ImportFailure(f"File not found: {path}")
    if path.stat().st_size > MAX_BYTES:
        raise ImportFailure("File is larger than 5 MB.")
    result = ImportResult()
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                raise ImportFailure("File is empty.")
            mapping = {h: _ALIASES.get(h.strip().lower()) for h in reader.fieldnames}
            present = {v for v in mapping.values() if v}
            if not _REQUIRED <= present:
                raise ImportFailure("Missing column(s): " + ", ".join(sorted(_REQUIRED - present)))
            for row_no, row in enumerate(reader, start=2):          # row 1 is the header
                if row_no - 1 > MAX_ROWS:
                    result.errors.append((row_no, f"Stopped: more than {MAX_ROWS} rows."))
                    break
                if None in row:
                    result.errors.append((row_no, "Too many columns in row."))
                    continue
                clean = {mapping[h]: (v or "") for h, v in row.items() if mapping.get(h)}
                try:
                    rec = validate_record(clean)
                    if ledger.is_duplicate(rec):
                        raise ValidationError("Duplicate of an existing entry.")
                    ledger.add(rec["date"], rec["kind"], rec["category"], rec["amount"], rec["note"])
                    result.imported += 1
                except ValidationError as exc:
                    result.errors.append((row_no, str(exc)))
    except UnicodeDecodeError:
        raise ImportFailure("File is not valid UTF-8 text.") from None
    except csv.Error as exc:
        raise ImportFailure(f"Not a readable CSV file: {exc}") from None
    return result


def write_error_log(result: ImportResult, source, log_path) -> Path:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"Import of {source}: {result.imported} imported, {result.skipped} skipped", ""]
    lines += [f"Row {n}: {msg}" for n, msg in result.errors]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path
