from thb.core.schemas import Trace
from thb.families import f02_website, f05_youtube
from thb.eval.scoring import score_submission
from thb.eval.trace import audit_trace
from thb.validate.oracle import OracleSolver


def _oracle_trace(result, out, submission=None):
    token, events = OracleSolver(out).solve(result.private_manifest)
    return Trace(task_id=result.task_id, agent_id="oracle",
                 model_id="oracle",
                 final_submission=submission if submission is not None
                 else token,
                 events=events)


def test_oracle_trace_scores_near_perfect(tmp_path):
    out = str(tmp_path / "world")
    result = f02_website.generate(3, "training", out, "W")
    trace = _oracle_trace(result, out)
    report = score_submission(trace, result.private_manifest)
    m = report["metrics"]
    assert m["final_token_success"] == 1.0
    assert m["partial_clue_progress"] == 1.0
    assert m["source_accuracy_score"] == 1.0
    assert m["citation_quality_score"] == 1.0
    assert m["robustness_score"] == 1.0
    assert m["trace_plausibility_score"] == 1.0
    assert report["composite_score"] > 0.95


def test_wrong_submission_scores_zero_token(tmp_path):
    out = str(tmp_path / "world")
    result = f02_website.generate(4, "training", out, "W")
    trace = _oracle_trace(result, out,
                          submission="THB{wrongwrongwrongwrong}")
    report = score_submission(trace, result.private_manifest)
    assert report["metrics"]["final_token_success"] == 0.0
    # fake-token-shaped wrong answer also hits robustness
    assert report["metrics"]["robustness_score"] <= 0.5


def test_answer_without_evidence_flagged(tmp_path):
    out = str(tmp_path / "world")
    result = f05_youtube.generate(5, "training", out, "W")
    bare = Trace(task_id=result.task_id, agent_id="cheater", model_id="x",
                 final_submission=result.token, events=[])
    audit = audit_trace(bare, result.private_manifest)
    assert audit["issues"]
    report = score_submission(bare, result.private_manifest)
    assert report["metrics"]["final_token_success"] == 1.0
    assert report["metrics"]["partial_clue_progress"] == 0.0
    assert report["metrics"]["trace_plausibility_score"] <= 0.2


def test_missing_api_evidence_lowers_source_accuracy(tmp_path):
    out = str(tmp_path / "world")
    result = f02_website.generate(6, "training", out, "W")
    token, events = OracleSolver(out).solve(result.private_manifest)
    trimmed = [e for e in events if not e["tool"].startswith("api")]
    trace = Trace(task_id=result.task_id, agent_id="a", model_id="m",
                  final_submission=token, events=trimmed)
    report = score_submission(trace, result.private_manifest)
    assert report["metrics"]["source_accuracy_score"] == 0.0
    assert report["metrics"]["partial_clue_progress"] < 1.0


def test_decoy_following_penalized(tmp_path):
    out = str(tmp_path / "world")
    result = f02_website.generate(7, "training", out, "W")
    token, events = OracleSolver(out).solve(result.private_manifest)
    events.append({"tool": "github.read_file", "target": "x",
                   "note": "followed_decoy"})
    trace = Trace(task_id=result.task_id, agent_id="a", model_id="m",
                  final_submission=token, events=events)
    report = score_submission(trace, result.private_manifest)
    assert report["metrics"]["robustness_score"] <= 0.5
