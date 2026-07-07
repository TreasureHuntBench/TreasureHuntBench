from thb.core.cache import SourceCache, make_cache_id, hash_raw
from thb.core.schemas import (
    CacheEntry, ClueNode, WorldArtifact, SkillDef,
    PublicManifest, PrivateManifest, Trace, TraceEvent,
)


def test_schema_roundtrips():
    node = ClueNode(
        node_id="n1", artifact_type="github_file",
        location={"repo": "r", "path": "records/L1S1_7Q_route.md"},
        tool="github", observation="repository=r2",
        normalization="none", validation="run_ref=L1S1-7Q2K",
        next_node="n2", skill_ids=["s1"])
    assert ClueNode.from_json(node.to_json()) == node

    art = WorldArtifact(artifact_id="a1", kind="repo",
                        public_location={"repo": "r"},
                        decoy_status="decoy", invalid_rule="run_ref mismatch")
    assert WorldArtifact.from_json(art.to_json()) == art

    skill = SkillDef(skill_id="get_gold_price", description="d",
                     introduced_in="L2S1", required_in=["L10S1"])
    assert SkillDef.from_json(skill.to_json()) == skill

    pub = PublicManifest(task_id="THB-TR-L1S1-7Q2K", split="training",
                         level_family="basic",
                         start={"repository": "x", "file": "y"},
                         allowed_tools=["github"], approved_sources=[],
                         answer_format="THB{...}")
    assert PublicManifest.from_json(pub.to_json()) == pub

    priv = PrivateManifest(task_id="t", run_id="L1S1-7Q2K", seed=3,
                           level_family="basic", split="training",
                           final_token_hash="sha256:x",
                           clue_graph=[node.to_dict()],
                           world_graph=[art.to_dict()],
                           skill_graph=[skill.to_dict()])
    back = PrivateManifest.from_json(priv.to_json())
    assert back == priv
    assert back.clue_nodes()[0] == node
    assert back.artifacts()[0] == art
    assert back.skills()[0] == skill

    tr = Trace(task_id="t", agent_id="a", model_id="m", final_submission="x")
    tr.add(TraceEvent(tool="github.read_file", target="r/p.md"))
    assert Trace.from_json(tr.to_json()).event_objs()[0].tool == "github.read_file"


def test_cache_id_deterministic_and_query_sensitive():
    q = {"city": "Passau", "date": "2017-01-12"}
    assert make_cache_id("Open-Meteo", q) == make_cache_id("Open-Meteo", dict(q))
    assert make_cache_id("Open-Meteo", q) != make_cache_id("Open-Meteo",
                                                           {**q, "date": "2017-01-13"})


def test_hash_raw_stable_across_key_order():
    assert hash_raw({"a": 1, "b": 2}) == hash_raw({"b": 2, "a": 1})
    assert hash_raw("x") != hash_raw("y")


def test_cache_put_get_lookup(tmp_path):
    cache = SourceCache(str(tmp_path / "cache"))
    q = {"city": "Passau", "date": "2017-01-12", "timezone": "Europe/Berlin"}
    entry = cache.put(
        source="Open-Meteo Historical Weather API", query=q,
        raw={"hourly": {"temperature_2m": [-8.1, -9.0]}},
        normalization_rule="min hourly temperature; tie -> earliest hour",
        normalized_value="03",
        citation="Open-Meteo Historical Weather API",
        source_url="https://archive-api.open-meteo.com/v1/archive?...")
    assert cache.get(entry.cache_id) == entry
    assert cache.lookup("Open-Meteo Historical Weather API", q) == entry
    assert cache.lookup("Open-Meteo Historical Weather API",
                        {**q, "date": "2000-01-01"}) is None
    assert entry.cache_id in cache.ids()
    assert isinstance(entry, CacheEntry)
    assert entry.retrieved_at.endswith("Z")
