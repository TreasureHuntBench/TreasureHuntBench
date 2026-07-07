"""Core data schemas for TreasureHuntBench.

All benchmark structures are plain dataclasses with lossless JSON
round-tripping (``to_dict`` / ``from_dict`` / ``to_json`` / ``from_json``).
They are shared by the generator, validators, publishers, and evaluator.
"""

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class _Jsonable:
    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        fields = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in fields}
        return cls(**kwargs)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False,
                          sort_keys=True)

    @classmethod
    def from_json(cls, text: str):
        return cls.from_dict(json.loads(text))


@dataclass
class CacheEntry(_Jsonable):
    """One cached external-source observation used for scoring."""
    cache_id: str
    source: str
    query: Dict[str, Any]
    normalization_rule: str
    normalized_value: str
    raw_response_hash: str
    retrieved_at: str            # ISO-8601 UTC
    citation: str
    source_url: str = ""


@dataclass
class ClueNode(_Jsonable):
    """One step of the intended (private) clue path."""
    node_id: str
    artifact_type: str           # e.g. github_file, youtube_video, api_value,
                                 # csv_row, zip_archive, git_history, branch
    location: Dict[str, Any]     # type-specific locator (repo/path/url/...)
    tool: str                    # tool the agent is expected to use
    observation: str             # exactly what the oracle extracts here
    normalization: str = ""      # deterministic rule applied to observation
    validation: str = ""         # explicit rule separating real from decoys
    source_cache_id: str = ""    # CacheEntry backing an external value
    next_node: str = ""          # node_id of the next step ('' = terminal)
    skill_ids: List[str] = field(default_factory=list)


@dataclass
class WorldArtifact(_Jsonable):
    """One visible (or decoy) artifact in the world graph."""
    artifact_id: str
    kind: str                    # repo, file, branch, issue, video, playlist,
                                 # archive, database, release, commit
    public_location: Dict[str, Any]
    decoy_status: str = "real"   # real | decoy
    invalid_rule: str = ""       # for decoys: the explicit rule they violate
    content_hash: str = ""
    source_dependencies: List[str] = field(default_factory=list)
    skill_dependencies: List[str] = field(default_factory=list)
    world_id: str = ""
    level_id: str = ""
    sublevel_id: str = ""
    split: str = ""


@dataclass
class SkillDef(_Jsonable):
    """A skill tracked by the skill graph."""
    skill_id: str
    description: str
    introduced_in: str
    practiced_in: List[str] = field(default_factory=list)
    required_in: List[str] = field(default_factory=list)
    memory_required: bool = True
    card_path: str = ""          # public artifact containing the skill card


@dataclass
class PublicManifest(_Jsonable):
    """Manifest visible to agents."""
    task_id: str
    split: str
    level_family: str
    start: Dict[str, Any]
    allowed_tools: List[str]
    approved_sources: List[str]
    answer_format: str
    step_budget: int = 200
    time_budget_minutes: int = 60
    memory_mode: str = "level_persistent"
    citation_policy: str = "cite every external value used"


@dataclass
class PrivateManifest(_Jsonable):
    """Evaluator-only manifest. Never published."""
    task_id: str
    run_id: str
    seed: int
    level_family: str
    split: str
    final_token_hash: str
    clue_graph: List[Dict[str, Any]] = field(default_factory=list)
    world_graph: List[Dict[str, Any]] = field(default_factory=list)
    skill_graph: List[Dict[str, Any]] = field(default_factory=list)
    decoy_ids: List[str] = field(default_factory=list)
    cache_ids: List[str] = field(default_factory=list)
    oracle_trace: List[Dict[str, Any]] = field(default_factory=list)
    validation_reports: Dict[str, Any] = field(default_factory=dict)

    def clue_nodes(self) -> List[ClueNode]:
        return [ClueNode.from_dict(d) for d in self.clue_graph]

    def artifacts(self) -> List[WorldArtifact]:
        return [WorldArtifact.from_dict(d) for d in self.world_graph]

    def skills(self) -> List[SkillDef]:
        return [SkillDef.from_dict(d) for d in self.skill_graph]


@dataclass
class TraceEvent(_Jsonable):
    """One agent action in a submission trace."""
    tool: str
    target: str = ""
    query: Dict[str, Any] = field(default_factory=dict)
    extracted: Dict[str, Any] = field(default_factory=dict)
    normalized_value: str = ""
    citation: str = ""
    note: str = ""


@dataclass
class Trace(_Jsonable):
    """A full agent submission trace."""
    task_id: str
    agent_id: str
    model_id: str
    final_submission: str
    events: List[Dict[str, Any]] = field(default_factory=list)

    def event_objs(self) -> List[TraceEvent]:
        return [TraceEvent.from_dict(e) for e in self.events]

    def add(self, event: TraceEvent) -> None:
        self.events.append(event.to_dict())


def dump_many(items: List[_Jsonable]) -> List[Dict[str, Any]]:
    return [i.to_dict() for i in items]
