"""TreasureHuntBench command-line interface.

Subcommands:
    generate   generate one level or a whole world (with validation)
    validate   run leakage + one-answer validators over stored manifests
    solve      run the oracle solver for a task
    evaluate   score a submitted trace against a private manifest
    baseline   run the grep / search-only / oracle baselines
    publish    push a generated world's repositories to the live GitHub org
"""

import argparse
import json
import os
import sys

from .core.schemas import PrivateManifest, Trace
from .worldgen import DEFAULT_PLAN, FAMILY_MODULES, generate_world


def _load_private(private_root: str, task_id: str) -> PrivateManifest:
    path = os.path.join(private_root, "%s.json" % task_id)
    with open(path, encoding="utf-8") as fh:
        return PrivateManifest.from_json(fh.read())


def _iter_private(private_root: str):
    for name in sorted(os.listdir(private_root)):
        if name.endswith(".json"):
            with open(os.path.join(private_root, name),
                      encoding="utf-8") as fh:
                yield PrivateManifest.from_json(fh.read())


def cmd_generate(args) -> int:
    if args.family == "all":
        plan = DEFAULT_PLAN
    else:
        plan = [(int(args.family), args.sub)]
    summaries = generate_world(args.seed, args.split, args.out,
                               args.world_id, args.private,
                               plan=plan, validate=not args.no_validate)
    print(json.dumps(summaries, indent=2))
    return 0


def cmd_validate(args) -> int:
    from .validate.leakage import scan_level
    from .validate.one_answer import validate_one_answer
    ok = True
    for manifest in _iter_private(args.private):
        leak = scan_level(args.out, manifest)
        one = validate_one_answer(args.out, manifest)
        status = "OK" if (leak["ok"] and one["ok"]) else "FAIL"
        ok = ok and status == "OK"
        print("%s %s leakage=%s one_answer=%s"
              % (status, manifest.task_id, leak["ok"], one["ok"]))
        for v in leak["violations"] + one["problems"]:
            print("   - %s" % v)
    return 0 if ok else 1


def cmd_solve(args) -> int:
    from .validate.oracle import OracleSolver
    manifest = _load_private(args.private, args.task)
    token, events = OracleSolver(args.out).solve(manifest)
    print(json.dumps({"task_id": manifest.task_id, "recovered_token": token,
                      "steps": len(events)}, indent=2))
    return 0


def cmd_evaluate(args) -> int:
    from .eval.scoring import score_submission
    with open(args.trace, encoding="utf-8") as fh:
        trace = Trace.from_json(fh.read())
    manifest = _load_private(args.private, trace.task_id)
    report = score_submission(trace, manifest)
    print(json.dumps(report, indent=2))
    return 0


def cmd_baseline(args) -> int:
    if args.which == "grep":
        from .baselines.grep_baseline import solve
        verdict = solve(args.out)
        verdict.pop("report", None)
    elif args.which == "search":
        from .baselines.search_only import solve
        verdict = solve(args.out, args.run_id)
    else:
        from .baselines.oracle_agent import solve
        manifest = _load_private(args.private, args.task)
        verdict = solve(args.out, manifest)
        verdict.pop("trace", None)
    print(json.dumps(verdict, indent=2))
    return 0


def cmd_publish(args) -> int:
    from .gen.github_pub import (LiveGitHubPublisher, spec_from_mirror)
    github_root = os.path.join(args.out, "github")
    publisher = LiveGitHubPublisher()
    published = []
    for repo in sorted(os.listdir(github_root)):
        repo_dir = os.path.join(github_root, repo)
        if not os.path.isdir(repo_dir):
            continue
        if args.only and repo not in args.only:
            continue
        spec = spec_from_mirror(repo_dir)
        if args.dry_run:
            print("would publish %s (%d commits, %d branches)"
                  % (spec.name, len(spec.commits), len(spec.branches)))
            continue
        url = publisher.publish(spec)
        published.append(url)
        print("published %s" % url)
    if published:
        print("%d repositories published" % len(published))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="thb",
                                     description="TreasureHuntBench tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("generate", help="generate level(s)")
    p.add_argument("--family", default="all",
                   help="family number 1-10 or 'all'")
    p.add_argument("--sub", type=int, default=1)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--split", default="training",
                   choices=["training", "validation", "test"])
    p.add_argument("--out", required=True)
    p.add_argument("--private", required=True,
                   help="directory for private manifests")
    p.add_argument("--world-id", default="W1")
    p.add_argument("--no-validate", action="store_true")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("validate", help="validate a generated world")
    p.add_argument("--out", required=True)
    p.add_argument("--private", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("solve", help="oracle-solve a task")
    p.add_argument("--out", required=True)
    p.add_argument("--private", required=True)
    p.add_argument("--task", required=True)
    p.set_defaults(func=cmd_solve)

    p = sub.add_parser("evaluate", help="score a submission trace")
    p.add_argument("--trace", required=True)
    p.add_argument("--private", required=True)
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("baseline", help="run a baseline")
    p.add_argument("--which", required=True,
                   choices=["grep", "search", "oracle"])
    p.add_argument("--out", required=True)
    p.add_argument("--private")
    p.add_argument("--task")
    p.add_argument("--run-id", dest="run_id")
    p.set_defaults(func=cmd_baseline)

    p = sub.add_parser("publish", help="publish world repos to GitHub")
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", nargs="*")
    p.set_defaults(func=cmd_publish)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
