"""Generate the TreasureHuntBench MVP benchmark.

Layout produced:

    private/build/<split>/w<N>/        full world trees (gitignored)
    private/manifests/<split>/         private manifests (gitignored)
    benchmark/<split>/INDEX.md         public task index (committed)
    benchmark/<split>/tasks/<id>/public_manifest.json
    benchmark/training/answers.json    released answers + oracle traces
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thb.core.schemas import PrivateManifest
from thb.validate.oracle import OracleSolver
from thb.worldgen import generate_world

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLAN = {
    "training": [("w1", 1001), ("w2", 1002), ("w3", 1003)],
    "validation": [("w1", 2001), ("w2", 2002)],
    "test": [("w1", 3001), ("w2", 3002)],
}


def main() -> int:
    bench_root = os.path.join(ROOT, "benchmark")
    summary_all = {}
    for split, worlds in PLAN.items():
        split_dir = os.path.join(bench_root, split)
        tasks_dir = os.path.join(split_dir, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        index_rows = []
        answers = {}
        for wname, seed in worlds:
            out_root = os.path.join(ROOT, "private/build", split, wname)
            private_root = os.path.join(ROOT, "private/manifests", split)
            if os.path.isdir(out_root):
                shutil.rmtree(out_root)
            world_id = "THB-%s-%s" % (split.upper(), wname.upper())
            summaries = generate_world(seed=seed, split=split,
                                       out_root=out_root,
                                       world_id=world_id,
                                       private_root=private_root,
                                       validate=True)
            solver = OracleSolver(out_root)
            for s in summaries:
                task_id = s["task_id"]
                # copy the public manifest into benchmark/
                src = os.path.join(out_root, "tasks", task_id,
                                   "public_manifest.json")
                dst_dir = os.path.join(tasks_dir, task_id)
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy(src, os.path.join(dst_dir,
                                              "public_manifest.json"))
                index_rows.append((task_id, s["level_family"], wname,
                                   s["start_repo"], s["start_path"]))
                if split == "training":
                    with open(os.path.join(private_root,
                                           task_id + ".json"),
                              encoding="utf-8") as fh:
                        manifest = PrivateManifest.from_json(fh.read())
                    token, events = solver.solve(manifest)
                    answers[task_id] = {
                        "final_token": token,
                        "seed": seed,
                        "world": wname,
                        "oracle_trace": events,
                    }
            print("generated %s/%s: %d tasks" % (split, wname,
                                                 len(summaries)))
        # index file
        lines = ["# TreasureHuntBench — %s split" % split, "",
                 "| task_id | family | world | start repository | start file |",
                 "|---|---|---|---|---|"]
        for row in sorted(index_rows):
            lines.append("| %s | %s | %s | %s | %s |" % row)
        lines += ["", "%d tasks." % len(index_rows)]
        if split != "training":
            lines += ["", "Answers, seeds, and clue graphs for this split "
                          "are hidden. Submissions are scored by the "
                          "official evaluator (trace required)."]
        with open(os.path.join(split_dir, "INDEX.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        if split == "training":
            with open(os.path.join(split_dir, "answers.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(answers, fh, indent=1, sort_keys=True,
                          ensure_ascii=False)
        summary_all[split] = len(index_rows)
    print(json.dumps(summary_all, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
