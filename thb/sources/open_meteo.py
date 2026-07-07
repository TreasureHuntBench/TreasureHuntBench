"""Open-Meteo historical weather source.

Query shape: {"city": "Passau, Germany", "date": "2017-01-12",
              "timezone": "Europe/Berlin"}
Supported rules: "coldest_hour_two_digit", "warmest_hour_two_digit"
(tie-break: earliest hour, always).
"""

from typing import Any, Dict, Optional, Tuple

from .base import ExternalSource, SourceError, bundle
from ..core.cache import SourceCache
from ..core.schemas import CacheEntry


def city_coords(city: str) -> Tuple[float, float]:
    info = bundle()["cities"].get(city)
    if not info:
        raise SourceError("city not in approved gazetteer: %r" % city)
    return info["lat"], info["lon"]


def approved_cities():
    return sorted(bundle()["cities"])


class OpenMeteoSource(ExternalSource):
    name = "Open-Meteo Historical Weather API"
    citation = ("Open-Meteo Historical Weather API, "
                "https://open-meteo.com/en/docs/historical-weather-api")

    def source_url(self, query: Dict[str, Any]) -> str:
        lat, lon = city_coords(query["city"])
        return ("https://archive-api.open-meteo.com/v1/archive"
                "?latitude=%s&longitude=%s&start_date=%s&end_date=%s"
                "&hourly=temperature_2m&timezone=%s"
                % (lat, lon, query["date"], query["date"],
                   query["timezone"].replace("/", "%2F")))

    def fetch(self, query: Dict[str, Any]) -> Any:
        data = self._get(self.source_url(query))
        hourly = data.get("hourly") or {}
        if not hourly.get("time"):
            raise SourceError("no hourly data for %r" % query)
        return {"time": hourly["time"],
                "temperature_2m": hourly["temperature_2m"]}

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        return bundle()["open_meteo"].get(
            "%s|%s" % (query["city"], query["date"]))

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        temps = raw["temperature_2m"]
        if rule == "coldest_hour_two_digit":
            target = min(t for t in temps if t is not None)
        elif rule == "warmest_hour_two_digit":
            target = max(t for t in temps if t is not None)
        else:
            raise SourceError("unsupported rule for Open-Meteo: %r" % rule)
        return temps.index(target)  # earliest occurrence == tie-break


# rule implementations are hour indices; register the two-digit formatting
from .base import NORMALIZATION_RULES, _two_digit  # noqa: E402

NORMALIZATION_RULES.setdefault("coldest_hour_two_digit", _two_digit)
NORMALIZATION_RULES.setdefault("warmest_hour_two_digit", _two_digit)


def get_coldest_hour(city: str, date: str, cache: SourceCache,
                     timezone: str = "Europe/Berlin"
                     ) -> Tuple[str, CacheEntry]:
    """Skill helper: two-digit coldest hour ('03'), earliest on ties."""
    return OpenMeteoSource().resolve(
        {"city": city, "date": date, "timezone": timezone},
        "coldest_hour_two_digit", cache)
