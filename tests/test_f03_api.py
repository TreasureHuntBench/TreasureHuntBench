import csv
import io

from thb.core.cache import SourceCache
from thb.families import f03_api
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family3_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f03_api.generate(seed=303, split="training", out_root=out,
                              world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    nodes = result.private_manifest.clue_nodes()
    assert [n.artifact_type for n in nodes] == [
        "github_file", "api_value", "csv_row", "github_file", "terminal"]

    github = LocalMirrorPublisher(out)
    cache = SourceCache(out + "/cache")

    weather = nodes[1]
    entry = cache.get(weather.source_cache_id)
    assert entry.normalized_value == weather.observation
    assert entry.normalization_rule == "coldest_hour_two_digit"
    assert 0 <= int(weather.observation) <= 23

    # the hour-keyed table has exactly 24 rows and only the coldest hour
    # routes to the real document
    row_node = nodes[2]
    table = github.read_file(row_node.location["repo"],
                             row_node.location["path"])
    rows = {r["hour"]: r["document"]
            for r in csv.DictReader(io.StringIO(table))}
    assert len(rows) == 24
    assert rows[weather.observation] == nodes[3].location["path"]
    routed_targets = [d for d in rows.values()
                      if d == nodes[3].location["path"]]
    assert len(routed_targets) == 1

    assert github.read_file(nodes[4].location["repo"],
                            nodes[4].location["path"]).strip() == result.token

    skills = {s.skill_id for s in result.private_manifest.skills()}
    assert "get_coldest_hour" in skills


def test_family3_deterministic(tmp_path):
    a = f03_api.generate(9, "training", str(tmp_path / "a"), "W")
    b = f03_api.generate(9, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.run_id == b.run_id
