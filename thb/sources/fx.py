"""ECB reference exchange rates via the Frankfurter API.

Query shape: {"date": "2018-04-17", "base": "EUR", "symbol": "JPY"}.
Supported rules: "integer_part", "round_nearest_integer", "verbatim".
"""

from typing import Any, Dict, Optional, Tuple

from .base import ExternalSource, SourceError, bundle
from ..core.cache import SourceCache
from ..core.schemas import CacheEntry


class EcbFxSource(ExternalSource):
    name = "ECB reference exchange rates (Frankfurter API)"
    citation = ("European Central Bank reference exchange rates via the "
                "Frankfurter API, https://frankfurter.dev")

    def source_url(self, query: Dict[str, Any]) -> str:
        return ("https://api.frankfurter.dev/v1/%s?base=%s&symbols=%s"
                % (query["date"], query.get("base", "EUR"), query["symbol"]))

    def fetch(self, query: Dict[str, Any]) -> Any:
        data = self._get(self.source_url(query))
        if query["symbol"] not in data.get("rates", {}):
            raise SourceError("no %s rate for %s"
                              % (query["symbol"], query["date"]))
        return {"rate": data["rates"][query["symbol"]],
                "date": data["date"]}

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        if query.get("base", "EUR") != "EUR":
            return None
        rates = bundle()["fx_frankfurter"].get(query["date"])
        if rates and query["symbol"] in rates:
            return {"rate": rates[query["symbol"]], "date": query["date"]}
        return None

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        return raw["rate"]


def get_fx_rate(date: str, symbol: str, cache: SourceCache,
                base: str = "EUR",
                normalization: str = "integer_part"
                ) -> Tuple[str, CacheEntry]:
    return EcbFxSource().resolve(
        {"date": date, "base": base, "symbol": symbol}, normalization, cache)


def bundled_fx_dates():
    return sorted(bundle()["fx_frankfurter"])
