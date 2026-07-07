"""World graph builder: everything visible in the simulated world."""

from typing import Any, Dict, List, Optional

from ..core.schemas import WorldArtifact


class WorldGraph:
    def __init__(self, world_id: str, level_id: str, sublevel_id: str,
                 split: str):
        self.world_id = world_id
        self.level_id = level_id
        self.sublevel_id = sublevel_id
        self.split = split
        self.artifacts: List[WorldArtifact] = []

    def add(self, kind: str, public_location: Dict[str, Any],
            decoy_status: str = "real", invalid_rule: str = "",
            source_dependencies: Optional[List[str]] = None,
            skill_dependencies: Optional[List[str]] = None,
            content_hash: str = "") -> WorldArtifact:
        art = WorldArtifact(
            artifact_id="%s-a%03d" % (self.sublevel_id, len(self.artifacts) + 1),
            kind=kind, public_location=public_location,
            decoy_status=decoy_status, invalid_rule=invalid_rule,
            content_hash=content_hash,
            source_dependencies=list(source_dependencies or []),
            skill_dependencies=list(skill_dependencies or []),
            world_id=self.world_id, level_id=self.level_id,
            sublevel_id=self.sublevel_id, split=self.split)
        self.artifacts.append(art)
        return art

    def decoys(self) -> List[WorldArtifact]:
        return [a for a in self.artifacts if a.decoy_status == "decoy"]

    def check(self) -> List[str]:
        problems = []
        ids = [a.artifact_id for a in self.artifacts]
        if len(set(ids)) != len(ids):
            problems.append("duplicate artifact ids")
        for art in self.artifacts:
            if art.decoy_status == "decoy" and not art.invalid_rule:
                problems.append(
                    "decoy %s lacks an explicit invalid_rule" % art.artifact_id)
            if art.decoy_status not in ("real", "decoy"):
                problems.append("bad decoy_status on %s" % art.artifact_id)
            if not art.public_location:
                problems.append("artifact %s has no location" % art.artifact_id)
        return problems

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.artifacts]
