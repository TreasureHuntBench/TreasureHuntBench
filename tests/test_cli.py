import json
import os

from thb.cli import main
from thb.gen.github_pub import (LocalMirrorPublisher, spec_from_mirror)


def test_cli_generate_validate_solve_baseline(tmp_path, capsys):
    out = str(tmp_path / "world")
    private = str(tmp_path / "private")

    assert main(["generate", "--family", "1", "--seed", "42",
                 "--out", out, "--private", private]) == 0
    summary = json.loads(capsys.readouterr().out)
    task_id = summary[0]["task_id"]
    assert summary[0]["validated"]

    assert main(["validate", "--out", out, "--private", private]) == 0
    assert "OK" in capsys.readouterr().out

    assert main(["solve", "--out", out, "--private", private,
                 "--task", task_id]) == 0
    solved = json.loads(capsys.readouterr().out)
    assert solved["recovered_token"].startswith("THB{")

    assert main(["baseline", "--which", "grep", "--out", out]) == 0
    verdict = json.loads(capsys.readouterr().out)
    assert not verdict["solved"]

    assert main(["baseline", "--which", "oracle", "--out", out,
                 "--private", private, "--task", task_id]) == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["solved"]


def test_cli_evaluate(tmp_path, capsys):
    out = str(tmp_path / "world")
    private = str(tmp_path / "private")
    main(["generate", "--family", "2", "--seed", "9",
          "--out", out, "--private", private])
    task_id = json.loads(capsys.readouterr().out)[0]["task_id"]

    from thb.core.schemas import PrivateManifest, Trace
    from thb.validate.oracle import OracleSolver
    with open(os.path.join(private, task_id + ".json")) as fh:
        manifest = PrivateManifest.from_json(fh.read())
    token, events = OracleSolver(out).solve(manifest)
    trace = Trace(task_id=task_id, agent_id="t", model_id="m",
                  final_submission=token, events=events)
    trace_path = str(tmp_path / "trace.json")
    with open(trace_path, "w") as fh:
        fh.write(trace.to_json())

    assert main(["evaluate", "--trace", trace_path,
                 "--private", private]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["metrics"]["final_token_success"] == 1.0


def test_publish_dry_run_and_spec_roundtrip(tmp_path, capsys):
    out = str(tmp_path / "world")
    private = str(tmp_path / "private")
    main(["generate", "--family", "6", "--seed", "13",
          "--out", out, "--private", private])
    capsys.readouterr()

    assert main(["publish", "--out", out, "--dry-run"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines and all(l.startswith("would publish") for l in lines)

    # spec reconstruction reproduces the mirror when re-published locally
    github = LocalMirrorPublisher(out)
    repo = github.list_repos()[0]
    spec = spec_from_mirror(github.repo_dir(repo))
    before = github.history(repo)
    pub2 = LocalMirrorPublisher(str(tmp_path / "copy"))
    pub2.publish(spec)
    assert pub2.history(repo) == before
