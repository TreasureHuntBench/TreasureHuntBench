"""Write worlds/INDEX.md summarizing the published benchmark, verified
against the live GitHub organization."""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def org_repos():
    out = subprocess.run(
        ["gh", "api", "--paginate", "orgs/TreasureHuntBench/repos",
         "--jq", ".[].name"],
        capture_output=True, text=True, check=True).stdout
    return set(out.split())


def main() -> int:
    live = org_repos()
    with open(os.path.join(ROOT, "private/publish_state.json"),
              encoding="utf-8") as fh:
        published = json.load(fh)

    rows = []
    missing = []
    for key in sorted(published):
        split, world, repo = key.split("/", 2)
        name = ("thb-assets-%s-%s" % (split, world)
                if repo == "__assets__" else repo)
        ok = name in live
        if not ok:
            missing.append(name)
        rows.append((split, world, name, "yes" if ok else "MISSING"))

    lines = [
        "# TreasureHuntBench — Published Worlds Index", "",
        "Repositories published to https://github.com/TreasureHuntBench,",
        "verified against the live organization listing.", "",
        "- Training worlds: full public artifacts; answers and oracle "
        "traces released in `benchmark/training/answers.json`.",
        "- Validation worlds: public artifacts; answers, seeds, and clue "
        "graphs hidden (official evaluator scoring, trace required).",
        "- Test worlds: not published; held privately for controlled "
        "evaluation.", "",
        "| split | world | repository | live |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| %s | %s | [%s](https://github.com/TreasureHuntBench/%s) | %s |"
                     % (row[0], row[1], row[2], row[2], row[3]))
    lines += ["", "%d repositories (%d missing)." % (len(rows), len(missing))]
    with open(os.path.join(ROOT, "worlds/INDEX.md"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("rows=%d missing=%d" % (len(rows), len(missing)))
    if missing:
        print("missing:", missing[:10])
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
