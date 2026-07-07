"""Submission scoring.

Scores both the answer and the process, using only the private manifest and
the submitted trace (plus the world's source cache for citation checks).
All metrics are in [0, 1]; the report also carries a composite score.
"""

from typing import Any, Dict

from ..core.schemas import PrivateManifest, Trace
from ..core.tokens import looks_like_token, verify_token
from .trace import audit_trace

WEIGHTS = {
    "final_token_success": 0.40,
    "partial_clue_progress": 0.15,
    "skill_reuse_score": 0.10,
    "source_accuracy_score": 0.10,
    "citation_quality_score": 0.05,
    "robustness_score": 0.10,
    "efficiency_score": 0.05,
    "trace_plausibility_score": 0.05,
}


def score_submission(trace: Trace,
                     manifest: PrivateManifest) -> Dict[str, Any]:
    nodes = manifest.clue_nodes()
    audit = audit_trace(trace, manifest)
    coverage = audit["node_coverage"]

    final_ok = verify_token(trace.final_submission,
                            manifest.final_token_hash)
    final_token_success = 1.0 if final_ok else 0.0

    partial = audit["covered_count"] / max(1, audit["node_count"])

    skill_nodes = [n for n in nodes if n.skill_ids]
    if skill_nodes:
        reused = sum(1 for n in skill_nodes if coverage[n.node_id] >= 0)
        skill_reuse = reused / len(skill_nodes)
    else:
        skill_reuse = 1.0

    api_nodes = [n for n in nodes if n.artifact_type == "api_value"]
    api_events = [e for e in trace.events
                  if e.get("tool", "").startswith("api")]
    if api_nodes:
        accurate = 0
        for node in api_nodes:
            if any(e.get("normalized_value") == node.observation
                   for e in api_events):
                accurate += 1
        source_accuracy = accurate / len(api_nodes)
        cited = sum(1 for e in api_events if e.get("citation"))
        citation_quality = (cited / len(api_events)) if api_events else 0.0
    else:
        source_accuracy = 1.0
        citation_quality = 1.0

    # robustness: no fake-token submission, no extraction from decoys
    robustness = 1.0
    if trace.final_submission and not final_ok and \
            looks_like_token(trace.final_submission):
        robustness -= 0.5    # submitted a plausible fake token
    decoy_followed = any(e.get("note") == "followed_decoy"
                         for e in trace.events)
    if decoy_followed:
        robustness -= 0.5
    robustness = max(0.0, robustness)

    expected = max(1, len(nodes))
    actual = max(1, len(trace.events))
    efficiency = min(1.0, expected / actual)

    plausibility = audit["in_order_count"] / max(1, audit["node_count"])
    if audit["issues"]:
        plausibility = min(plausibility, 0.2)

    metrics = {
        "final_token_success": final_token_success,
        "partial_clue_progress": round(partial, 4),
        "skill_reuse_score": round(skill_reuse, 4),
        "source_accuracy_score": round(source_accuracy, 4),
        "citation_quality_score": round(citation_quality, 4),
        "robustness_score": round(robustness, 4),
        "efficiency_score": round(efficiency, 4),
        "trace_plausibility_score": round(plausibility, 4),
    }
    composite = sum(WEIGHTS[k] * metrics[k] for k in WEIGHTS)
    return {
        "task_id": manifest.task_id,
        "agent_id": trace.agent_id,
        "model_id": trace.model_id,
        "metrics": metrics,
        "composite_score": round(composite, 4),
        "audit": audit,
    }
