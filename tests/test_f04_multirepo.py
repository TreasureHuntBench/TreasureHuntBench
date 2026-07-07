import fnmatch
import re

from thb.families import f04_multirepo
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family4_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f04_multirepo.generate(seed=404, split="training", out_root=out,
                                    world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    nodes = result.private_manifest.clue_nodes()
    search = next(n for n in nodes if n.artifact_type == "github_repo_search")

    # several candidates match the pattern, exactly one carries the run id
    matches = [r for r in github.list_repos()
               if fnmatch.fnmatch(r, search.location["pattern"])]
    assert len(matches) == f04_multirepo.N_CANDIDATES
    valid = []
    for repo in matches:
        text = github.read_file(
            repo, search.location["check_path"].format(repo=repo))
        m = re.search(r"run_id:\s*(\S+)", text)
        if m and m.group(1) == search.location["check_value"]:
            valid.append(repo)
    assert valid == [search.location["expected_repo"]]

    # decoys recorded with explicit rules
    decoys = [a for a in result.private_manifest.artifacts()
              if a.decoy_status == "decoy" and a.kind == "repo"]
    assert len(decoys) == f04_multirepo.N_CANDIDATES - 1

    # the selected repo routes to the terminal token
    terminal = nodes[-1]
    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"]).strip() == result.token


def test_family4_deterministic(tmp_path):
    a = f04_multirepo.generate(11, "training", str(tmp_path / "a"), "W")
    b = f04_multirepo.generate(11, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.start_repo == b.start_repo
