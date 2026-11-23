"""JSON persistence with atomic saves and recovery from corrupted files."""
import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple

from .ledger import Ledger, default_settings
from .models import Transaction
from .validation import ValidationError, validate_record

SCHEMA_VERSION = 1


class Storage:
    def __init__(self, path):
        self.path = Path(path)

    def load(self) -> Tuple[Ledger, List[str]]:
        """Return (ledger, warnings). Never raises for missing/corrupt files."""
        warnings: List[str] = []
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return Ledger(), warnings
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            backup = self._quarantine()
            warnings.append(f"Data file was unreadable ({exc.__class__.__name__}); "
                            f"started fresh. Old file kept as {backup.name if backup else 'n/a'}.")
            return Ledger(), warnings

        if isinstance(data, list):                       # legacy: bare list of records
            data = {"transactions": data}
        if not isinstance(data, dict):
            backup = self._quarantine()
            warnings.append(f"Unexpected file layout; started fresh. Old file kept as "
                            f"{backup.name if backup else 'n/a'}.")
            return Ledger(), warnings

        transactions, seen = [], set()
        for n, raw in enumerate(data.get("transactions", []), start=1):
            try:
                if not isinstance(raw, dict):
                    raise ValidationError("record is not an object")
                tid = int(raw.get("id", 0))
                if tid < 1 or tid in seen:
                    raise ValidationError("missing or duplicate id")
                rec = validate_record(raw)
                transactions.append(Transaction(tid, **rec))
                seen.add(tid)
            except (ValidationError, TypeError, ValueError) as exc:
                warnings.append(f"Skipped stored record #{n}: {exc}")
        settings = default_settings()
        if isinstance(data.get("settings"), dict):
            settings.update({k: v for k, v in data["settings"].items() if k in settings})
        return Ledger(transactions, settings), warnings

    def save(self, ledger: Ledger) -> None:
        """Write to a temp file, then atomically swap it in so a crash never corrupts data."""
        payload = {
            "schema_version": SCHEMA_VERSION,
            "settings": ledger.settings,
            "transactions": [t.to_dict() for t in sorted(ledger.all(), key=lambda t: t.id)],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _quarantine(self):
        if not self.path.exists():
            return None
        backup = self.path.with_name(f"{self.path.stem}.corrupt-{datetime.now():%Y%m%d-%H%M%S}.json")
        try:
            os.replace(self.path, backup)
            return backup
        except OSError:
            return None
