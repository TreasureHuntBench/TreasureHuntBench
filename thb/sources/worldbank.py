"""World Bank Indicators API source.

Query shape: {"country": "DE", "indicator": "SP.POP.TOTL", "year": "2018"}.
Supported rules: "integer_part", "round_nearest_integer", "verbatim",
"millions_round" (value / 1e6 rounded to nearest integer).
"""

from typing import Any, Dict, Optional, Tuple

from .base import (ExternalSource, NORMALIZATION_RULES, SourceError, bundle)
from ..core.cache import SourceCache
from ..core.schemas import CacheEntry

NORMALIZATION_RULES.setdefault(
    "millions_round", lambda v: str(int(round(float(v) / 1e6))))


class WorldBankSource(ExternalSource):
    name = "World Bank Indicators API"
    citation = ("World Bank Indicators API, "
                "https://datahelpdesk.worldbank.org/knowledgebase/topics/125589")

    def source_url(self, query: Dict[str, Any]) -> str:
        return ("https://api.worldbank.org/v2/country/%s/indicator/%s"
                "?date=%s&format=json"
                % (query["country"], query["indicator"], query["year"]))

    def fetch(self, query: Dict[str, Any]) -> Any:
        data = self._get(self.source_url(query))
        try:
            value = data[1][0]["value"]
        except (IndexError, KeyError, TypeError):
            raise SourceError("no observation for %r" % query)
        if value is None:
            raise SourceError("null observation for %r" % query)
        return {"value": value}

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        key = "%s|%s|%s" % (query["country"], query["indicator"],
                            query["year"])
        value = bundle()["worldbank"].get(key)
        return None if value is None else {"value": value}

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        return raw["value"]


def get_series_observation(country: str, indicator: str, year: str,
                           cache: SourceCache,
                           normalization: str = "integer_part"
                           ) -> Tuple[str, CacheEntry]:
    return WorldBankSource().resolve(
        {"country": country, "indicator": indicator, "year": year},
        normalization, cache)
