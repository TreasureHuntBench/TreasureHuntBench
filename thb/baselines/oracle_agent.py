"""Oracle agent baseline: follows the private clue graph. Must succeed."""

from typing import Any, Dict

from ..core.schemas import PrivateManifest, Trace
from ..eval.scoring import score_submission
from ..validate.oracle import OracleSolver


def solve(out_root: str, manifest: PrivateManifest) -> Dict[str, Any]:
    token, events = OracleSolver(out_root).solve(manifest)
    trace = Trace(task_id=manifest.task_id, agent_id="oracle-baseline",
                  model_id="oracle", final_submission=token, events=events)
    report = score_submission(trace, manifest)
    return {"solved": report["metrics"]["final_token_success"] == 1.0,
            "score_report": report, "trace": trace.to_dict()}
