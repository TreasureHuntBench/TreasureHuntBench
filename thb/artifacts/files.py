"""Plain-file artifact writers (Markdown, JSON, CSV).

Writers make artifacts look like ordinary project files — reports, records,
ledgers — while carrying the operational instruction or keyed payload for a
level. All content is passed in by the level generator; nothing here invents
clue wording.
"""

import csv
import io
import json
import os
from typing import Any, Dict, List, Optional, Sequence


def _ensure_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_text(path: str, content: str) -> str:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def write_json(path: str, data: Any) -> str:
    return write_text(path, json.dumps(data, indent=2, ensure_ascii=False,
                                       sort_keys=True) + "\n")


def markdown_doc(title: str, sections: Sequence[Dict[str, str]],
                 front_matter: Optional[Dict[str, Any]] = None) -> str:
    """Assemble a Markdown document: optional front matter, title, sections.

    Each section is {"heading": ..., "body": ...}; heading may be empty.
    """
    parts = []
    if front_matter:
        parts.append("---")
        for key in sorted(front_matter):
            parts.append("%s: %s" % (key, front_matter[key]))
        parts.append("---")
        parts.append("")
    parts.append("# %s" % title)
    parts.append("")
    for sec in sections:
        if sec.get("heading"):
            parts.append("## %s" % sec["heading"])
            parts.append("")
        parts.append(sec["body"].rstrip())
        parts.append("")
    return "\n".join(parts)


def write_markdown(path: str, title: str, sections: Sequence[Dict[str, str]],
                   front_matter: Optional[Dict[str, Any]] = None) -> str:
    return write_text(path, markdown_doc(title, sections, front_matter))


def csv_text(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def write_csv(path: str, header: Sequence[str],
              rows: Sequence[Sequence[Any]]) -> str:
    return write_text(path, csv_text(header, rows))


def keyed_ledger_rows(key_values: List[str], payloads: Dict[str, List[Any]],
                      filler_payload, rng_stream) -> List[List[Any]]:
    """Rows keyed by first column; ``payloads`` maps key -> rest-of-row.

    Keys not in ``payloads`` receive filler produced by
    ``filler_payload(key, rng_stream)``.
    """
    rows = []
    for key in key_values:
        if key in payloads:
            rows.append([key] + list(payloads[key]))
        else:
            rows.append([key] + list(filler_payload(key, rng_stream)))
    return rows


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()
