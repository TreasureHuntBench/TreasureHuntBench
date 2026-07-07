"""Capture artifacts: timed recording readouts stored inside repositories.

A *capture file* is a WebVTT document committed to a repo. Header ``NOTE``
lines carry structured metadata (e.g. ``run_ref=L9S3-2D8A``); timed cues
carry the displayed lines. They replace YouTube videos in the video-free
benchmark profile: timestamp reasoning ("inspect 00:HH") works on cues, and
candidate validation works on the NOTE fields.

An *upload log* is a JSON file listing ordered entry titles; it replaces
playlist-order clues.
"""

import json
import re
from typing import Dict, List, Sequence, Tuple

Segment = Tuple[int, int, List[str]]     # start_sec, end_sec, lines


def _ts(seconds: int) -> str:
    return "%02d:%02d:%02d.000" % (seconds // 3600, (seconds % 3600) // 60,
                                   seconds % 60)


def build_capture_vtt(note_fields: Dict[str, str],
                      segments: Sequence[Segment]) -> str:
    parts = ["WEBVTT", ""]
    for key in sorted(note_fields):
        parts.append("NOTE %s=%s" % (key, note_fields[key]))
    if note_fields:
        parts.append("")
    for start, end, lines in segments:
        parts.append("%s --> %s" % (_ts(start), _ts(end)))
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts)


def parse_note_fields(vtt_text: str) -> Dict[str, str]:
    fields = {}
    for match in re.finditer(r"^NOTE (\S+?)=(.+)$", vtt_text, re.MULTILINE):
        fields[match.group(1)] = match.group(2).strip()
    return fields


def _cue_seconds(ts: str) -> int:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + int(float(s))


def cue_lines_at(vtt_text: str, timestamp: str) -> List[str]:
    """Lines of the cue covering 'MM:SS' (or 'HH:MM:SS')."""
    parts = timestamp.split(":")
    if len(parts) == 2:
        t = int(parts[0]) * 60 + int(parts[1])
    else:
        t = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    blocks = re.split(r"\n\s*\n", vtt_text)
    for block in blocks:
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if not lines or "-->" not in lines[0]:
            continue
        start_ts, end_ts = [p.strip() for p in lines[0].split("-->")]
        if _cue_seconds(start_ts) <= t < _cue_seconds(end_ts):
            return lines[1:]
    return []


def build_upload_log(titles: Sequence[str], log_kind: str = "uploads") -> str:
    return json.dumps(
        {"kind": log_kind,
         "entries": [{"position": i + 1, "title": t}
                     for i, t in enumerate(titles)]},
        indent=2, ensure_ascii=False) + "\n"


def parse_upload_log_titles(text: str) -> List[str]:
    data = json.loads(text)
    return [e["title"] for e in data["entries"]]
