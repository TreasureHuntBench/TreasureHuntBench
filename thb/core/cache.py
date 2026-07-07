"""External-source cache.

Every external value that matters for scoring is stored here at generation
time: the exact query, the raw response hash, the deterministic normalization
rule, the normalized value, retrieval timestamp, and a citation record.
Validators and the evaluator read only this cache — never live APIs.
"""

import datetime
import hashlib
import json
import os
from typing import Any, Dict, Optional

from .schemas import CacheEntry


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def hash_raw(raw: Any) -> str:
    if isinstance(raw, bytes):
        payload = raw
    elif isinstance(raw, str):
        payload = raw.encode("utf-8")
    else:
        payload = _canonical(raw).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def make_cache_id(source: str, query: Dict[str, Any]) -> str:
    digest = hashlib.sha256(
        (source + "|" + _canonical(query)).encode("utf-8")).hexdigest()[:16]
    slug = "".join(c if c.isalnum() else "-" for c in source.upper())[:24]
    return "CACHE-%s-%s" % (slug.strip("-"), digest.upper())


class SourceCache:
    """A directory of CacheEntry JSON files keyed by cache_id."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, cache_id: str) -> str:
        return os.path.join(self.root, cache_id + ".json")

    def put(self, source: str, query: Dict[str, Any], raw: Any,
            normalization_rule: str, normalized_value: str,
            citation: str, source_url: str = "") -> CacheEntry:
        entry = CacheEntry(
            cache_id=make_cache_id(source, query),
            source=source,
            query=query,
            normalization_rule=normalization_rule,
            normalized_value=str(normalized_value),
            raw_response_hash=hash_raw(raw),
            retrieved_at=datetime.datetime.utcnow().replace(
                microsecond=0).isoformat() + "Z",
            citation=citation,
            source_url=source_url,
        )
        with open(self._path(entry.cache_id), "w", encoding="utf-8") as fh:
            fh.write(entry.to_json())
        return entry

    def get(self, cache_id: str) -> Optional[CacheEntry]:
        path = self._path(cache_id)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return CacheEntry.from_json(fh.read())

    def lookup(self, source: str, query: Dict[str, Any]) -> Optional[CacheEntry]:
        return self.get(make_cache_id(source, query))

    def ids(self):
        if not os.path.isdir(self.root):
            return []
        return sorted(os.path.splitext(f)[0] for f in os.listdir(self.root)
                      if f.endswith(".json"))
