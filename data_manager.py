# utils/data_manager.py
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# On Streamlit Cloud the repo is mounted read-only.
# Use /tmp for writable storage; fall back to local data/ for local dev.
_local_data = Path(__file__).parent.parent / "data"
try:
    _local_data.mkdir(parents=True, exist_ok=True)
    _test = _local_data / ".write_test"
    _test.write_text("ok")
    _test.unlink()
    DATA_DIR = _local_data
except OSError:
    DATA_DIR = Path("/tmp/family_budget_data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class DataManager:
    def __init__(self):
        self.portfolio_file = DATA_DIR / "portfolio.json"
        self.income_file    = DATA_DIR / "income.json"
        self.expenses_file  = DATA_DIR / "expenses.json"
        self.cache_file     = DATA_DIR / "prices_cache.json"
        self._init_files()

    # ── File helpers ──────────────────────────────────────────────────────────

    def _load(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: Path, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _init_files(self):
        defaults = {
            self.portfolio_file: {"investments": []},
            self.income_file:    {"entries": []},
            self.expenses_file:  {"entries": []},
            self.cache_file:     {"prices": {}, "updated": {}},
        }
        for path, default in defaults.items():
            if not path.exists():
                self._save(path, default)

    # ── Portfolio / Investments ───────────────────────────────────────────────

    def get_portfolio(self) -> dict:
        return self._load(self.portfolio_file)

    def get_investments(self) -> List[dict]:
        return self.get_portfolio().get("investments", [])

    def add_investment(self, inv: dict) -> str:
        portfolio = self.get_portfolio()
        inv["id"] = str(uuid.uuid4())
        inv["added_date"] = datetime.now().isoformat()
        portfolio["investments"].append(inv)
        self._save(self.portfolio_file, portfolio)
        return inv["id"]

    def remove_investment(self, inv_id: str):
        portfolio = self.get_portfolio()
        portfolio["investments"] = [
            i for i in portfolio["investments"] if i["id"] != inv_id
        ]
        self._save(self.portfolio_file, portfolio)

    def update_investment(self, inv_id: str, updates: dict):
        portfolio = self.get_portfolio()
        for inv in portfolio["investments"]:
            if inv["id"] == inv_id:
                inv.update(updates)
                break
        self._save(self.portfolio_file, portfolio)

    # ── Income ────────────────────────────────────────────────────────────────

    def get_income(self, year: int = None, month: int = None) -> List[dict]:
        entries = self._load(self.income_file)["entries"]
        if year:
            entries = [e for e in entries if e.get("year") == year]
        if month:
            entries = [e for e in entries if e.get("month") == month]
        return entries

    def add_income(self, entry: dict):
        data = self._load(self.income_file)
        entry["id"] = str(uuid.uuid4())
        data["entries"].append(entry)
        self._save(self.income_file, data)

    def remove_income(self, entry_id: str):
        data = self._load(self.income_file)
        data["entries"] = [e for e in data["entries"] if e.get("id") != entry_id]
        self._save(self.income_file, data)

    # ── Expenses ──────────────────────────────────────────────────────────────

    def get_expenses(self, year: int = None, month: int = None) -> List[dict]:
        entries = self._load(self.expenses_file)["entries"]
        if year:
            entries = [e for e in entries if e.get("year") == year]
        if month:
            entries = [e for e in entries if e.get("month") == month]
        return entries

    def add_expense(self, entry: dict):
        data = self._load(self.expenses_file)
        entry["id"] = str(uuid.uuid4())
        data["entries"].append(entry)
        self._save(self.expenses_file, data)

    def remove_expense(self, entry_id: str):
        data = self._load(self.expenses_file)
        data["entries"] = [e for e in data["entries"] if e.get("id") != entry_id]
        self._save(self.expenses_file, data)

    # ── Price Cache ───────────────────────────────────────────────────────────

    def get_cached_price(self, key: str) -> Optional[dict]:
        cache = self._load(self.cache_file)
        return cache["prices"].get(key)

    def set_cached_price(self, key: str, price_data: dict):
        cache = self._load(self.cache_file)
        cache["prices"][key] = price_data
        cache["updated"][key] = datetime.now().isoformat()
        self._save(self.cache_file, cache)

    def is_price_fresh(self, key: str) -> bool:
        """Return True if cached price is from today."""
        cached = self.get_cached_price(key)
        if not cached:
            return False
        cached_date = cached.get("date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        return cached_date == today

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_all_years_months(self) -> List[tuple]:
        """Return sorted list of (year, month) that have any data."""
        income   = self._load(self.income_file)["entries"]
        expenses = self._load(self.expenses_file)["entries"]
        ym_set = set()
        for e in income + expenses:
            if "year" in e and "month" in e:
                ym_set.add((e["year"], e["month"]))
        return sorted(ym_set, reverse=True)
