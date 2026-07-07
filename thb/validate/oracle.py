"""Oracle solver.

Walks a private clue graph *mechanically* over the local world (GitHub
mirror, YouTube mirror, source cache) and recovers the final token. A level
is only releasable if the oracle recovers a token whose hash matches the
private manifest. The walk also produces an oracle trace in the standard
trace-event format.
"""

import csv
import fnmatch
import io
import json
import re
from typing import Any, Dict, List, Tuple

from ..artifacts.archive import read_zip_entry
from ..artifacts.encodings import acrostic_decode, caesar_decode
from ..core.cache import SourceCache
from ..core.schemas import ClueNode, PrivateManifest, TraceEvent
from ..core.tokens import token_hash
from ..gen.github_pub import LocalMirrorPublisher
from ..gen.youtube_pub import YouTubeMirror


class OracleError(Exception):
    pass


def _field_value(text: str, field: str) -> str:
    """Extract a field from JSON content or front-matter/key-value text."""
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            return str(json.loads(text).get(field, ""))
        except ValueError:
            pass
    match = re.search(r"^%s\s*[:=]\s*(\S+)\s*$" % re.escape(field),
                      text, re.MULTILINE)
    return match.group(1) if match else ""


class OracleSolver:
    def __init__(self, out_root: str):
        self.github = LocalMirrorPublisher(out_root)
        self.youtube = YouTubeMirror(out_root)
        self.cache = SourceCache(out_root + "/cache")

    def solve(self, manifest: PrivateManifest
              ) -> Tuple[str, List[Dict[str, Any]]]:
        """Return (recovered_token, oracle_trace_events)."""
        events: List[TraceEvent] = []
        token = ""
        for node in manifest.clue_nodes():
            handler = getattr(self, "_" + node.artifact_type, None)
            if handler is None:
                raise OracleError("no handler for artifact type %r"
                                  % node.artifact_type)
            observed = handler(node, events)
            if node.artifact_type == "terminal":
                token = observed
        if not token:
            raise OracleError("clue graph has no terminal node")
        if token_hash(token) != manifest.final_token_hash:
            raise OracleError("recovered token hash mismatch")
        return token, [e.to_dict() for e in events]

    # ---- node handlers -------------------------------------------------

    def _read(self, node: ClueNode) -> str:
        return self.github.read_file(node.location["repo"],
                                     node.location["path"],
                                     node.location.get("branch", "main"))

    def _github_file(self, node: ClueNode, events) -> str:
        text = self._read(node)
        if node.observation not in text:
            # multi-part observations: every whitespace-separated part
            parts = node.observation.split()
            if not parts or not all(p in text for p in parts):
                raise OracleError("expected observation missing at %s"
                                  % node.node_id)
        events.append(TraceEvent(
            tool="github.read_file",
            target="%s/%s" % (node.location["repo"], node.location["path"])))
        return text

    _branch_doc = _github_file

    def _api_value(self, node: ClueNode, events) -> str:
        entry = self.cache.lookup(node.location["source"],
                                  node.location["query"])
        if entry is None:
            raise OracleError("no cache entry for %s" % node.node_id)
        if entry.normalization_rule != node.location["rule"]:
            raise OracleError("normalization rule mismatch at %s"
                              % node.node_id)
        if entry.normalized_value != node.observation:
            raise OracleError("cached value %r != expected %r at %s"
                              % (entry.normalized_value, node.observation,
                                 node.node_id))
        events.append(TraceEvent(
            tool="api.%s" % node.location["source"],
            query=node.location["query"],
            normalized_value=entry.normalized_value,
            citation=entry.citation))
        return entry.normalized_value

    def _vtt_timestamp(self, node: ClueNode, events) -> str:
        from ..artifacts.captures import cue_lines_at
        text = self._read(node)
        lines = cue_lines_at(text, node.location["timestamp"])
        joined = "\n".join(lines)
        if joined != node.observation:
            raise OracleError("capture cue mismatch at %s" % node.node_id)
        events.append(TraceEvent(
            tool="file.capture_inspect",
            target="%s/%s" % (node.location["repo"], node.location["path"]),
            query={"timestamp": node.location["timestamp"]},
            extracted={"lines": lines}))
        return joined

    def _vtt_candidates(self, node: ClueNode, events) -> str:
        from ..artifacts.captures import cue_lines_at, parse_note_fields
        loc = node.location
        listing = json.loads(self.github.read_file(
            loc["list_repo"], loc["list_path"]))
        valid = []
        for path in listing["capture_paths"]:
            text = self.github.read_file(loc["list_repo"], path)
            fields = parse_note_fields(text)
            if fields.get(loc["check_field"]) == loc["check_value"]:
                valid.append(path)
        if valid != [loc["expected_path"]]:
            raise OracleError("capture filtering not unique at %s: %r"
                              % (node.node_id, valid))
        text = self.github.read_file(loc["list_repo"], valid[0])
        lines = cue_lines_at(text, loc["timestamp"])
        joined = "\n".join(lines)
        if joined != node.observation:
            raise OracleError("valid-capture cue mismatch at %s"
                              % node.node_id)
        events.append(TraceEvent(
            tool="file.capture_verify_and_inspect",
            target="%s/%s" % (loc["list_repo"], valid[0]),
            query={"timestamp": loc["timestamp"],
                   "validation": "%s=%s" % (loc["check_field"],
                                            loc["check_value"])},
            extracted={"lines": lines}))
        return joined

    def _titles_list(self, node: ClueNode, events) -> str:
        from ..artifacts.captures import parse_upload_log_titles
        loc = node.location
        titles = parse_upload_log_titles(
            self.github.read_file(loc["repo"], loc["path"]))
        last = titles[-loc["last_n"]:]
        raw = acrostic_decode(last)
        if loc["method"] != "caesar":
            raise OracleError("unsupported decode method at %s" % node.node_id)
        decoded = caesar_decode(raw, loc["shift"])
        if decoded != node.observation:
            raise OracleError("decoded tag mismatch at %s" % node.node_id)
        events.append(TraceEvent(
            tool="file.upload_log_titles",
            target="%s/%s" % (loc["repo"], loc["path"]),
            extracted={"raw": raw, "decoded": decoded}))
        return decoded

    def _youtube_timestamp(self, node: ClueNode, events) -> str:
        lines = self.youtube.text_at(node.location["video_ref"],
                                     node.location["timestamp"])
        text = "\n".join(lines)
        if text != node.observation:
            raise OracleError("video text mismatch at %s" % node.node_id)
        events.append(TraceEvent(
            tool="youtube.inspect",
            target=node.location["video_ref"],
            query={"timestamp": node.location["timestamp"]},
            extracted={"lines": lines}))
        return text

    def _youtube_candidates(self, node: ClueNode, events) -> str:
        listing = json.loads(self.github.read_file(
            node.location["list_repo"], node.location["list_path"]))
        marker = "%s=%s" % (node.location["check_field"],
                            node.location["check_value"])
        valid = [ref for ref in listing["video_refs"]
                 if marker in self.youtube.metadata(ref)["description"]]
        if valid != [node.location["expected_ref"]]:
            raise OracleError("candidate filtering not unique at %s: %r"
                              % (node.node_id, valid))
        lines = self.youtube.text_at(valid[0], node.location["timestamp"])
        text = "\n".join(lines)
        if text != node.observation:
            raise OracleError("valid-video text mismatch at %s" % node.node_id)
        events.append(TraceEvent(
            tool="youtube.verify_and_inspect", target=valid[0],
            query={"timestamp": node.location["timestamp"],
                   "validation": marker},
            extracted={"lines": lines}))
        return text

    def _playlist_titles(self, node: ClueNode, events) -> str:
        playlist = self.youtube.playlist(node.location["playlist_ref"])
        titles = playlist["video_titles"][-node.location["last_n"]:]
        raw = acrostic_decode(titles)
        if node.location["method"] != "caesar":
            raise OracleError("unsupported decode method at %s" % node.node_id)
        decoded = caesar_decode(raw, node.location["shift"])
        if decoded != node.observation:
            raise OracleError("decoded tag mismatch at %s" % node.node_id)
        events.append(TraceEvent(
            tool="youtube.playlist_titles",
            target=node.location["playlist_ref"],
            extracted={"raw": raw, "decoded": decoded}))
        return decoded

    def _github_repo_search(self, node: ClueNode, events) -> str:
        loc = node.location
        matches = [r for r in self.github.list_repos()
                   if fnmatch.fnmatch(r, loc["pattern"])]
        valid = []
        for repo in matches:
            try:
                text = self.github.read_file(
                    repo, loc["check_path"].format(repo=repo))
            except OSError:
                continue
            if _field_value(text, loc["check_field"]) != loc["check_value"]:
                continue
            if "check2_field" in loc and _field_value(
                    text, loc["check2_field"]) != loc["check2_value"]:
                continue
            valid.append(repo)
        if valid != [loc["expected_repo"]]:
            raise OracleError("repo filtering not unique at %s: %r"
                              % (node.node_id, valid))
        events.append(TraceEvent(
            tool="github.search_repositories",
            query={"pattern": loc["pattern"]},
            extracted={"matches": matches, "selected": valid[0]}))
        return valid[0]

    def _git_history(self, node: ClueNode, events) -> str:
        loc = node.location
        history = self.github.history(loc["repo"])[loc.get("branch", "main")]
        messages = [h["message"] for h in history]
        if loc["before_message"] not in messages:
            raise OracleError("anchor commit missing at %s" % node.node_id)
        idx = messages.index(loc["before_message"])
        if idx == 0:
            raise OracleError("no commit before anchor at %s" % node.node_id)
        files = history[idx - 1]["files"]
        if loc["path"] not in files:
            raise OracleError("path missing in pre-anchor commit at %s"
                              % node.node_id)
        content = files[loc["path"]]
        if isinstance(content, dict):  # binary snapshot
            raise OracleError("binary payload unsupported at %s"
                              % node.node_id)
        if node.observation not in content:
            raise OracleError("expected payload missing at %s" % node.node_id)
        events.append(TraceEvent(
            tool="github.git_history", target=loc["repo"],
            query={"before_message": loc["before_message"],
                   "path": loc["path"]}))
        return content

    def _csv_row(self, node: ClueNode, events) -> str:
        text = self._read(node)
        body = "\n".join(l for l in text.splitlines()
                         if not l.startswith("#"))
        reader = csv.reader(io.StringIO(body))
        rows = list(reader)
        header, data = rows[0], rows[1:]
        key = str(node.location["key"])
        hits = [row for row in data if row and row[0] == key]
        if len(hits) != 1:
            raise OracleError("csv key not unique at %s" % node.node_id)
        row_text = " ".join(hits[0])
        for part in node.observation.split():
            if part not in row_text:
                raise OracleError("expected row payload missing at %s"
                                  % node.node_id)
        events.append(TraceEvent(
            tool="file.csv_row",
            target="%s/%s" % (node.location["repo"], node.location["path"]),
            query={"key": key}, extracted={"row": hits[0]}))
        return row_text

    def _zip_entry(self, node: ClueNode, events) -> str:
        loc = node.location
        zip_path = self.github.file_path(loc["repo"], loc["path"],
                                         loc.get("branch", "main"))
        content = read_zip_entry(zip_path, loc["arcname"],
                                 password=loc.get("password"))
        if node.observation not in content:
            raise OracleError("archive payload mismatch at %s" % node.node_id)
        events.append(TraceEvent(
            tool="archive.read_entry",
            target="%s/%s" % (loc["repo"], loc["path"]),
            query={"arcname": loc["arcname"]}))
        return content

    def _terminal(self, node: ClueNode, events) -> str:
        text = self._read(node).strip()
        events.append(TraceEvent(
            tool="github.read_file",
            target="%s/%s" % (node.location["repo"], node.location["path"]),
            note="terminal artifact"))
        return text
