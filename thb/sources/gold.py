"""Approved gold-price source (Yahoo Finance GC=F daily close, USD).

TreasureHuntBench's "approved gold-price source" is the COMEX gold futures
front-month daily close as served by the Yahoo Finance chart API, cached at
generation time. Query shape: {"symbol": "GC=F", "date": "2018-04-17"}.
Supported rules: "round_nearest_integer", "integer_part".

Generators must pick trading days; a date with no close is a SourceError and
the generator retries with a different date.
"""

import datetime as _dt
from typing import Any, Dict, Optional, Tuple

import requests

from .base import ExternalSource, SourceError, bundle
from ..core.cache import SourceCache
from ..core.schemas import CacheEntry

APPROVED_GOLD_SYMBOL = "GC=F"
_YAHOO_UA = {"User-Agent": "Mozilla/5.0 (TreasureHuntBench benchmark)"}


class GoldPriceSource(ExternalSource):
    name = "Approved gold-price source (Yahoo Finance GC=F daily close, USD)"
    citation = ("Yahoo Finance chart API, symbol GC=F (COMEX gold futures), "
                "daily close in USD")

    def source_url(self, query: Dict[str, Any]) -> str:
        day = _dt.datetime.strptime(query["date"], "%Y-%m-%d")
        p1 = int(day.replace(tzinfo=_dt.timezone.utc).timestamp())
        return ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
                "?period1=%d&period2=%d&interval=1d"
                % (query.get("symbol", APPROVED_GOLD_SYMBOL), p1,
                   p1 + 2 * 86400))

    def fetch(self, query: Dict[str, Any]) -> Any:
        try:
            resp = requests.get(self.source_url(query), headers=_YAHOO_UA,
                                timeout=30)
            resp.raise_for_status()
            result = resp.json()["chart"]["result"][0]
        except Exception as exc:  # noqa: BLE001
            raise SourceError("gold fetch failed: %s" % exc)
        closes = {}
        quote = result["indicators"]["quote"][0]["close"]
        for ts, close in zip(result.get("timestamp", []), quote):
            if close is not None:
                day = _dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                closes[day] = close
        if query["date"] not in closes:
            raise SourceError("no gold close for %s (not a trading day?)"
                              % query["date"])
        return {"close_usd": closes[query["date"]]}

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        if query.get("symbol", APPROVED_GOLD_SYMBOL) != APPROVED_GOLD_SYMBOL:
            return None
        return bundle()["gold_yahoo"].get(query["date"])

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        return raw["close_usd"]


def get_gold_price(date: str, cache: SourceCache,
                   normalization: str = "round_nearest_integer"
                   ) -> Tuple[str, CacheEntry]:
    """Skill helper: normalized USD gold close for a trading date."""
    return GoldPriceSource().resolve(
        {"symbol": APPROVED_GOLD_SYMBOL, "date": date}, normalization, cache)


def bundled_gold_dates():
    return sorted(bundle()["gold_yahoo"])
