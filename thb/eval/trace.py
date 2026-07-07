"""Trace auditing: match submitted trace events against the private clue
graph to establish which intended steps are actually evidenced."""

from typing import Any, Dict, List

from ..core.schemas import ClueNode, PrivateManifest, Trace


def _covers(node: ClueNode, event: Dict[str, Any]) -> bool:
    tool = event.get("tool", "")
    target = event.get("target", "")
    query = event.get("query", {}) or {}
    value = event.get("normalized_value", "")
    loc = node.location
    if node.artifact_type in ("github_file", "branch_doc", "terminal",
                              "csv_row"):
        return (tool.startswith(("github", "file"))
                and loc.get("repo", "") in target
                and loc.get("path", "") in target)
    if node.artifact_type == "api_value":
        same_query = all(str(query.get(k)) == str(v)
                         for k, v in loc.get("query", {}).items())
        return (tool.startswith("api") and
                (value == node.observation or same_query))
    if node.artifact_type in ("vtt_timestamp", "vtt_candidates"):
        path = loc.get("path") or loc.get("expected_path", "")
        return (tool.startswith(("file", "github"))
                and path in target
                and query.get("timestamp") == loc.get("timestamp"))
    if node.artifact_type == "titles_list":
        return (tool.startswith(("file", "github"))
                and loc.get("path", "") in target)
    if node.artifact_type in ("youtube_timestamp", "youtube_candidates"):
        ref = loc.get("video_ref") or loc.get("expected_ref", "")
        return (tool.startswith("youtube") and ref in target
                and query.get("timestamp") == loc.get("timestamp"))
    if node.artifact_type == "playlist_titles":
        return (tool.startswith("youtube")
                and loc.get("playlist_ref", "") in target)
    if node.artifact_type == "github_repo_search":
        return (tool.startswith("github")
                and query.get("pattern") == loc.get("pattern"))
    if node.artifact_type == "git_history":
        return (tool.startswith("github")
                and query.get("before_message") == loc.get("before_message"))
    if node.artifact_type == "zip_entry":
        return (tool.startswith("archive")
                and query.get("arcname") == loc.get("arcname"))
    return False


def audit_trace(trace: Trace, manifest: PrivateManifest) -> Dict[str, Any]:
    nodes = manifest.clue_nodes()
    events = trace.events
    coverage: Dict[str, int] = {}
    cursor = 0
    in_order = 0
    for node in nodes:
        found = -1
        for i, event in enumerate(events):
            if _covers(node, event):
                found = i
                break
        coverage[node.node_id] = found
        if found >= cursor:
            in_order += 1
            cursor = found
    covered = [n for n in nodes if coverage[n.node_id] >= 0]
    issues: List[str] = []
    if trace.final_submission and not covered:
        issues.append("submission without any evidenced path step")
    terminal = nodes[-1]
    if trace.final_submission and coverage[terminal.node_id] < 0:
        issues.append("submission without visiting the terminal artifact")
    return {
        "node_coverage": coverage,
        "covered_count": len(covered),
        "node_count": len(nodes),
        "in_order_count": in_order,
        "issues": issues,
    }
