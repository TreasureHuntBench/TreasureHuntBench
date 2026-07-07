import csv
import fnmatch
import io
import json
import os

import pytest

from thb.artifacts.archive import read_zip_entry
from thb.artifacts.encodings import caesar_decode
from thb.families import f08_memory, f10_grand
from thb.artifacts.captures import cue_lines_at
from thb.gen.github_pub import LocalMirrorPublisher
from thb.graphs.skills import SkillGraph

from families_common import assert_family_contract, grep_baseline_fails


def _world(tmp_path, seed=1010):
    out = str(tmp_path / "world")
    skills = SkillGraph()
    memory = {}
    f08_memory.generate(seed, "training", out, "W-TEST", sub_num=1,
                        skill_graph=skills, world_memory=memory)
    result = f10_grand.generate(seed, "training", out, "W-TEST",
                                skill_graph=skills, world_memory=memory)
    return out, result


def test_family10_full_chain(tmp_path):
    out, result = _world(tmp_path)
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    chain = result.private_manifest.clue_nodes()

    # the capture shows the market routing fields at the derived second
    cap_node = next(n for n in chain
                    if n.artifact_type == "vtt_timestamp")
    vtt = github.read_file(cap_node.location["repo"],
                           cap_node.location["path"])
    lines = cue_lines_at(vtt, cap_node.location["timestamp"])
    assert "series_id=GC=F" in lines
    assert any(l.startswith("observation_date=") for l in lines)

    # repo search: pattern matches N candidates, both checks needed
    search = next(n for n in chain
                  if n.artifact_type == "github_repo_search")
    matches = [r for r in github.list_repos()
               if fnmatch.fnmatch(r, search.location["pattern"])]
    assert len(matches) == f10_grand.N_CANDIDATES
    valid = []
    for repo in matches:
        manifest = json.loads(github.read_file(
            repo, search.location["check_path"].format(repo=repo)))
        if (manifest.get("run_ref") == search.location["check_value"] and
                manifest.get("artifact_state") ==
                search.location["check2_value"]):
            valid.append(repo)
    assert valid == [search.location["expected_repo"]]

    # git history holds the encoded branch; decode matches the real branch
    hist = next(n for n in chain if n.artifact_type == "git_history")
    history = github.history(hist.location["repo"])["main"]
    messages = [h["message"] for h in history]
    idx = messages.index(hist.location["before_message"])
    payload = history[idx - 1]["files"][hist.location["path"]]
    assert hist.observation in payload
    branch = caesar_decode(hist.observation, f10_grand.SHIFT)
    assert branch == result.notes["branch"]

    # CSV row keyed by MARKET_KEY yields the archive and its password
    row_node = next(n for n in chain if n.artifact_type == "csv_row")
    table = github.read_file(row_node.location["repo"],
                             row_node.location["path"],
                             branch=row_node.location["branch"])
    body = "\n".join(l for l in table.splitlines()
                     if not l.startswith("#"))
    rows = {r["market_key"]: r for r in csv.DictReader(io.StringIO(body))}
    row = rows[row_node.location["key"]]
    zip_node = next(n for n in chain if n.artifact_type == "zip_entry")
    assert row["archive_file"] == zip_node.location["path"]
    assert row["archive_key"] == zip_node.location["password"]

    # ZIP opens only with the password; Arabic doc names the terminal path
    zip_path = github.file_path(zip_node.location["repo"],
                                zip_node.location["path"],
                                zip_node.location["branch"])
    assert os.path.exists(zip_path)
    ar_doc = read_zip_entry(zip_path, zip_node.location["arcname"],
                            password=zip_node.location["password"])
    terminal = chain[-1]
    assert terminal.location["path"] in ar_doc
    with pytest.raises(Exception):
        read_zip_entry(zip_path, zip_node.location["arcname"],
                       password="wrong")

    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"],
                            branch=terminal.location["branch"]
                            ).strip() == result.token


def test_family10_requires_memory(tmp_path):
    with pytest.raises(ValueError):
        f10_grand.generate(1, "training", str(tmp_path / "w"), "W",
                           world_memory={})


def test_family10_deterministic(tmp_path):
    _, a = _world(tmp_path / "a", seed=77)
    _, b = _world(tmp_path / "b", seed=77)
    assert a.token == b.token and a.notes == b.notes
