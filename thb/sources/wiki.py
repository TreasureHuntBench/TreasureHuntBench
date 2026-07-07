"""Wikipedia / Wikidata source.

Two query shapes:
  {"qid": "Q4190", "lang": "de"}            -> Wikidata label in a language
  {"page": "Passau", "field": "wikibase_item"} -> Wikipedia REST summary field

Supported rule: "verbatim".
"""

from typing import Any, Dict, Optional, Tuple

from .base import ExternalSource, SourceError, bundle
from ..core.cache import SourceCache
from ..core.schemas import CacheEntry


def city_qid(city: str) -> str:
    info = bundle()["cities"].get(city)
    if not info:
        raise SourceError("city not in approved gazetteer: %r" % city)
    return info["wikidata_qid"]


class WikidataLabelSource(ExternalSource):
    name = "Wikidata entity labels"
    citation = ("Wikidata entity data, "
                "https://www.wikidata.org/wiki/Special:EntityData")

    def source_url(self, query: Dict[str, Any]) -> str:
        return ("https://www.wikidata.org/wiki/Special:EntityData/%s.json"
                % query["qid"])

    def fetch(self, query: Dict[str, Any]) -> Any:
        data = self._get(self.source_url(query))
        entity = data["entities"][query["qid"]]
        labels = {lang: rec["value"]
                  for lang, rec in entity.get("labels", {}).items()}
        if query["lang"] not in labels:
            raise SourceError("no %s label on %s"
                              % (query["lang"], query["qid"]))
        return {"labels": {query["lang"]: labels[query["lang"]]}}

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        labels = bundle()["wikidata_labels"].get(query["qid"], {})
        if query["lang"] in labels:
            return {"labels": {query["lang"]: labels[query["lang"]]}}
        return None

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        return raw["labels"][query["lang"]]


class WikipediaSummarySource(ExternalSource):
    name = "Wikipedia REST page summary"
    citation = ("Wikimedia REST API page summary, "
                "https://en.wikipedia.org/api/rest_v1/")

    def source_url(self, query: Dict[str, Any]) -> str:
        return ("https://en.wikipedia.org/api/rest_v1/page/summary/%s"
                % query["page"].replace(" ", "_"))

    def fetch(self, query: Dict[str, Any]) -> Any:
        data = self._get(self.source_url(query))
        field = query.get("field", "wikibase_item")
        if field not in data:
            raise SourceError("field %r missing on page %r"
                              % (field, query["page"]))
        return {query.get("field", "wikibase_item"): data[field]}

    def fetch_bundled(self, query: Dict[str, Any]) -> Optional[Any]:
        # Bundled coverage: wikibase_item for approved cities only.
        if query.get("field", "wikibase_item") != "wikibase_item":
            return None
        for city, info in bundle()["cities"].items():
            if city.split(",")[0].strip() == query["page"].replace("_", " "):
                return {"wikibase_item": info["wikidata_qid"]}
        return None

    def extract(self, raw: Any, query: Dict[str, Any], rule: str) -> Any:
        return raw[query.get("field", "wikibase_item")]


def get_wikidata_label(qid: str, lang: str, cache: SourceCache
                       ) -> Tuple[str, CacheEntry]:
    return WikidataLabelSource().resolve(
        {"qid": qid, "lang": lang}, "verbatim", cache)


def get_wikibase_item(page: str, cache: SourceCache
                      ) -> Tuple[str, CacheEntry]:
    return WikipediaSummarySource().resolve(
        {"page": page, "field": "wikibase_item"}, "verbatim", cache)
