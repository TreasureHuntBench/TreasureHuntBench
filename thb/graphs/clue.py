"""Clue graph builder: the private intended path for one sub-level."""

from typing import Any, Dict, List, Optional

from ..core.schemas import ClueNode


class ClueChain:
    """A linear chain of clue nodes with automatic linking."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.nodes: List[ClueNode] = []

    def add(self, artifact_type: str, location: Dict[str, Any], tool: str,
            observation: str, normalization: str = "", validation: str = "",
            source_cache_id: str = "",
            skill_ids: Optional[List[str]] = None) -> ClueNode:
        node = ClueNode(
            node_id="%s-n%02d" % (self.run_id, len(self.nodes) + 1),
            artifact_type=artifact_type, location=location, tool=tool,
            observation=observation, normalization=normalization,
            validation=validation, source_cache_id=source_cache_id,
            skill_ids=list(skill_ids or []))
        if self.nodes:
            self.nodes[-1].next_node = node.node_id
        self.nodes.append(node)
        return node

    @property
    def start(self) -> ClueNode:
        return self.nodes[0]

    @property
    def terminal(self) -> ClueNode:
        return self.nodes[-1]

    def check(self) -> List[str]:
        """Return integrity problems (empty list = OK)."""
        problems = []
        if not self.nodes:
            return ["clue chain is empty"]
        ids = [n.node_id for n in self.nodes]
        if len(set(ids)) != len(ids):
            problems.append("duplicate node ids")
        for i, node in enumerate(self.nodes):
            is_last = i == len(self.nodes) - 1
            if is_last and node.next_node:
                problems.append("terminal node %s has next_node" % node.node_id)
            if not is_last and node.next_node != self.nodes[i + 1].node_id:
                problems.append("broken link at %s" % node.node_id)
            if not node.location:
                problems.append("node %s has no location" % node.node_id)
            if not node.observation:
                problems.append("node %s has no expected observation"
                                % node.node_id)
        return problems

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in self.nodes]
