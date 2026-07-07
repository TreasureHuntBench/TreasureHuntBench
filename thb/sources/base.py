"""External source interface.

Each source exposes ``fetch`` (live), ``fetch_bundled`` (offline snapshot),
``normalize`` (named deterministic rules), ``cite``, and ``resolve`` which
ties them together with the world :class:`~thb.core.cache.SourceCache`:

    cache hit  ->  use cached normalized value
    bundled    ->  use offline snapshot shipped with the package
    live       ->  fetch from the real API

Whatever path produced the value, it is written to the world cache so that
validators and the evaluator never need network access again.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

import requests

from ..core.cache import SourceCache
from ..core.schemas import CacheEntry

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "bundled.json")
_BUNDLE = None

USER_AGENT = {"User-Agent":
              "TreasureHuntBench/0.1 (benchmark world generator)"}


def bundle() -> Dict[str, Any]:
    global _BUNDLE
    if _BUNDLE is None:
        with open(_DATA_PATH, encoding="utf-8") as fh:
            _BUNDLE = json.load(fh)
    return _BUNDLE


class SourceError(Exception):
    pass


def _round_nearest_integer(value: Any) -> str:
    return str(int(round(float(value))))


def _integer_part(value: Any) -> str:
    return str(int(float(value)))


def _two_digit(value: Any) -> str:
    return "%02d" % int(value)


def _verbatim(value: Any) -> str:
    return str(value)


NORMALIZATION_RULES = {
    "round_nearest_integer": _round_nearest_integer,
    "integer_part": _integer_part,
    "two_digit": _two_digit,
    "verbatim": _verbatim,
}


def apply_rule(rule: str, value: Any) -> str:
    if rule not in NORMALIZATION_RULES:
        raise SourceError("unknown normalization rule: %r" % rule)
    return NORMALIZATION_RULES[rule](value)


class ExternalSource:
    """Base class for approved external sources."""

    name = "abstract"
    citation = "abstract"

    def fetch(self, query: Dict[str, Any]) -> Any:
        """Live API fetch. Raises SourceError on failure."""
        raise NotImplementedError

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        """Offline snapshot lookup; None when the query is not bundled."""
        raise NotImplementedError

    def source_url(self, query: Dict[str, Any]) -> str:
        return ""

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        """Pull the scalar of interest out of the raw response."""
        raise NotImplementedError

    # ------------------------------------------------------------------

    def _get(self, url: str, timeout: int = 30) -> Any:
        try:
            resp = requests.get(url, headers=USER_AGENT, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - normalized error path
            raise SourceError("%s fetch failed: %s" % (self.name, exc))

    def resolve(self, query: Dict[str, Any], rule: str,
                cache: SourceCache) -> Tuple[str, CacheEntry]:
        """Return (normalized_value, cache_entry), consulting cache first."""
        hit = cache.lookup(self.name, query)
        if hit is not None and hit.normalization_rule == rule:
            return hit.normalized_value, hit
        raw = self.fetch_bundled(query)
        if raw is None:
            raw = self.fetch(query)
        value = apply_rule(rule, self.extract(raw, query, rule))
        entry = cache.put(source=self.name, query=query, raw=raw,
                          normalization_rule=rule, normalized_value=value,
                          citation=self.citation,
                          source_url=self.source_url(query))
        return value, entry
