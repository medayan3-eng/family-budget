# utils/price_fetcher.py
"""
Price fetching logic:
  - US stocks / ETFs  → yfinance (ticker as-is, e.g. "AAPL", "SPY")
  - TASE stocks       → yfinance with .TA suffix (e.g. "TEVA.TA")
  - Israeli funds     → tries yfinance with {fund_id}.TA first,
                        then falls back to TASE public API,
                        then returns None (user must set price manually)
  - Manual assets     → uses stored price, no network call
"""

import requests
import yfinance as yf
from datetime import datetime
from typing import Optional


# ── Exchange rate ─────────────────────────────────────────────────────────────

def get_usd_ils_rate() -> float:
    """Live USD→ILS rate via yfinance. Falls back to 3.70 if unavailable."""
    try:
        ticker = yf.Ticker("USDILS=X")
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 3.70


# ── Individual fetchers ───────────────────────────────────────────────────────

def _fetch_yfinance(ticker: str) -> Optional[dict]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        change     = price - prev
        change_pct = (change / prev * 100) if prev else 0
        info = t.info
        return {
            "price":      round(price, 4),
            "change":     round(change, 4),
            "change_pct": round(change_pct, 2),
            "currency":   info.get("currency", "USD"),
            "name":       info.get("longName") or info.get("shortName") or ticker,
            "source":     "yfinance",
            "date":       hist.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception:
        return None


def _fetch_tase_fund(fund_id: str) -> Optional[dict]:
    """
    Try the TASE public REST API for Israeli mutual fund NAV.
    fund_id is the 7-digit Israeli fund number (מספר קרן).
    """
    try:
        url = "https://api.tase.co.il/api/fund/GetFundDetails"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "he",
            "User-Agent": "Mozilla/5.0",
        }
        r = requests.get(url, params={"FundId": fund_id, "lang": 1},
                         headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                # Field names vary by TASE API version — try several
                nav = (data.get("NAV") or data.get("nav")
                       or data.get("NetAssetValue") or data.get("netAssetValue"))
                name = (data.get("FundName") or data.get("fundName")
                        or data.get("Name") or fund_id)
                if nav:
                    return {
                        "price":      float(nav),
                        "change":     0.0,
                        "change_pct": 0.0,
                        "currency":   "ILS",
                        "name":       name,
                        "source":     "tase_api",
                        "date":       datetime.now().strftime("%Y-%m-%d"),
                    }
    except Exception:
        pass
    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def fetch_asset_price(asset: dict) -> Optional[dict]:
    """
    Given an investment dict, return up-to-date price data or None.
    asset must contain at least {"type": "us_stock"|"tase_stock"|"israeli_fund"|"manual", ...}
    """
    asset_type = asset.get("type", "us_stock")

    if asset_type == "us_stock":
        return _fetch_yfinance(asset["ticker"])

    elif asset_type == "tase_stock":
        raw = asset["ticker"].upper().replace(".TA", "")
        return _fetch_yfinance(f"{raw}.TA")

    elif asset_type == "israeli_fund":
        fund_id = asset.get("fund_id", "")
        # 1) Try yfinance (some funds are listed there)
        result = _fetch_yfinance(f"{fund_id}.TA")
        if result:
            result["currency"] = "ILS"
            return result
        # 2) Try TASE API
        result = _fetch_tase_fund(fund_id)
        if result:
            return result
        return None  # caller will fall back to cached/manual price

    elif asset_type == "manual":
        # No network call; return stored price as-is
        return {
            "price":      float(asset.get("manual_price", 0)),
            "change":     0.0,
            "change_pct": 0.0,
            "currency":   asset.get("currency", "ILS"),
            "name":       asset.get("name", "נכס ידני"),
            "source":     "manual",
            "date":       asset.get("manual_price_date", datetime.now().strftime("%Y-%m-%d")),
        }

    return None


def fetch_all_prices(investments: list, dm) -> dict:
    """
    Fetch/cache prices for all investments.
    Returns dict: {investment_id → price_data}
    """
    today = datetime.now().strftime("%Y-%m-%d")
    prices = {}

    for inv in investments:
        inv_id   = inv["id"]
        cache_key = inv.get("ticker") or inv.get("fund_id") or inv_id

        # Use cached price if it's from today
        if dm.is_price_fresh(cache_key):
            prices[inv_id] = dm.get_cached_price(cache_key)
            continue

        # Fetch fresh price
        price_data = fetch_asset_price(inv)

        if price_data:
            dm.set_cached_price(cache_key, price_data)
            prices[inv_id] = price_data
        else:
            # Fall back to stale cache if available
            stale = dm.get_cached_price(cache_key)
            if stale:
                stale["stale"] = True
                prices[inv_id] = stale

    return prices
