"""Shared level-assembly framework for all level families.

Every sub-level generator builds a :class:`LevelBuilder`, adds artifacts and
clue nodes, and calls :meth:`LevelBuilder.finalize`. The builder owns the
run-id, final token, RNG, naming forge, source cache, GitHub mirror, YouTube
mirror, and the three graphs, and writes the public/private manifest pair.

Clue-node ``artifact_type`` contract (interpreted by the oracle solver):

    github_file        location {repo, path, branch?}   read file text
    github_repo_search location {pattern, expected_repo, check_path,
                                 check_field, check_value}
    api_value          location {source, query, rule}   via source cache
    youtube_timestamp  location {video_ref, timestamp}  mirror text lines
    youtube_candidates location {list_repo, list_path, check_field,
                                 check_value, expected_ref, timestamp}
    playlist_titles    location {playlist_ref, last_n}  first-char acrostic
    git_history        location {repo, before_message, path}
    csv_row            location {repo, path, branch?, key}
    zip_entry          location {repo, path, arcname, password_from}
    branch_doc         location {repo, branch, path}
    terminal           location {repo, path, branch?}   file whose single
                       line is the final token

``observation`` holds the exact value/text the oracle must find there.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..artifacts.files import write_json
from ..core.cache import SourceCache
from ..core.naming import NameForge, make_run_id
from ..core.rng import TaskRng
from ..core.schemas import PrivateManifest, PublicManifest
from ..core.tokens import ANSWER_FORMAT, mint_token, token_hash
from ..gen.github_pub import LocalMirrorPublisher, RepoSpec
from ..gen.youtube_pub import YouTubeMirror
from ..graphs.clue import ClueChain
from ..graphs.skills import SkillGraph
from ..graphs.world import WorldGraph

FAMILY_NAMES = {
    1: "basic_clue_following",
    2: "real_website_navigation",
    3: "api_historical_data",
    4: "multi_repository_search",
    5: "youtube_timestamp_and_metadata",
    6: "multilingual_cross_lingual",
    7: "encoded_hidden_messages",
    8: "memory_and_skill_transfer",
    9: "decoys_and_verification",
    10: "grand_multi_source_hunt",
}

SPLIT_CODES = {"training": "TR", "validation": "VAL", "test": "TEST"}


@dataclass
class LevelResult:
    task_id: str
    run_id: str
    public_manifest: PublicManifest
    private_manifest: PrivateManifest
    repos: List[RepoSpec]
    start_repo: str
    start_path: str
    token: str = ""            # kept only in-memory / private storage
    notes: Dict[str, Any] = field(default_factory=dict)


class LevelBuilder:
    def __init__(self, family_num: int, sub_num: int, seed: int, split: str,
                 out_root: str, world_id: str,
                 skill_graph: Optional[SkillGraph] = None,
                 world_memory: Optional[Dict[str, Any]] = None):
        self.family_num = family_num
        self.sub_num = sub_num
        self.seed = seed
        self.split = split
        self.out_root = out_root
        self.world_id = world_id
        self.rng = TaskRng(seed).child("L%dS%d" % (family_num, sub_num))
        self.run_id = make_run_id(family_num, sub_num, self.rng)
        self.forge = NameForge(self.run_id, self.rng)
        self.token = mint_token(self.rng, self.run_id)
        self.task_id = "THB-%s-%s" % (SPLIT_CODES[split],
                                      self.run_id.replace("-", "-", 1))
        self.level_tag = self.run_id.split("-")[0]
        self.cache = SourceCache(os.path.join(out_root, "cache"))
        self.github = LocalMirrorPublisher(out_root)
        self.youtube = YouTubeMirror(out_root)
        self.chain = ClueChain(self.run_id)
        self.world = WorldGraph(world_id, "L%d" % family_num,
                                self.level_tag, split)
        self.skills = skill_graph if skill_graph is not None else SkillGraph()
        self.memory = world_memory if world_memory is not None else {}
        self.repos: List[RepoSpec] = []
        self._cache_ids: List[str] = []

    # ------------------------------------------------------------------

    def new_repo(self, name: str, description: str = "") -> RepoSpec:
        spec = RepoSpec(name=name, description=description)
        self.repos.append(spec)
        return spec

    def resolve_source(self, source_obj, query, rule) -> str:
        value, entry = source_obj.resolve(query, rule, self.cache)
        self._cache_ids.append(entry.cache_id)
        return value

    def last_cache_id(self) -> str:
        return self._cache_ids[-1] if self._cache_ids else ""

    def terminal_file_content(self) -> str:
        return self.token + "\n"

    # ------------------------------------------------------------------

    def finalize(self, start_repo: str, start_path: str,
                 allowed_tools: List[str], approved_sources: List[str],
                 step_budget: int = 200,
                 notes: Optional[Dict[str, Any]] = None) -> LevelResult:
        # token-noise: a fake token-shaped string in the start repo makes a
        # blind THB{...} regex sweep ambiguous by construction
        from ..gen.decoys import fake_token
        noise_path = "packets/%s_%s_sample.txt" % (
            self.level_tag, self.rng.code("noise", 3))
        noise = fake_token(self.rng, "world_noise", self.token)
        if self.repos:
            self.repos[0].add_commit("add sample packet",
                                     {noise_path: noise + "\n"})
            self.world.add(
                "file",
                {"repo": self.repos[0].name, "path": noise_path},
                decoy_status="decoy",
                invalid_rule="token-shaped string never referenced by any "
                             "instruction on the intended path")

        problems = self.chain.check() + self.world.check()
        if problems:
            raise ValueError("level integrity problems: %s" % problems)
        if self.chain.terminal.artifact_type != "terminal":
            raise ValueError("last clue node must be terminal")
        for spec in self.repos:
            self.github.publish(spec)
        public = PublicManifest(
            task_id=self.task_id, split=self.split,
            level_family=FAMILY_NAMES[self.family_num],
            start={"type": "github_repository",
                   "organization": "TreasureHuntBench",
                   "repository": start_repo, "file": start_path},
            allowed_tools=allowed_tools,
            approved_sources=approved_sources,
            answer_format=ANSWER_FORMAT,
            step_budget=step_budget)
        private = PrivateManifest(
            task_id=self.task_id, run_id=self.run_id, seed=self.seed,
            level_family=FAMILY_NAMES[self.family_num], split=self.split,
            final_token_hash=token_hash(self.token),
            clue_graph=self.chain.to_dicts(),
            world_graph=self.world.to_dicts(),
            skill_graph=self.skills.to_dicts(),
            decoy_ids=[a.artifact_id for a in self.world.decoys()],
            cache_ids=list(dict.fromkeys(self._cache_ids)))
        tasks_dir = os.path.join(self.out_root, "tasks", self.task_id)
        write_json(os.path.join(tasks_dir, "public_manifest.json"),
                   public.to_dict())
        return LevelResult(
            task_id=self.task_id, run_id=self.run_id,
            public_manifest=public, private_manifest=private,
            repos=self.repos, start_repo=start_repo, start_path=start_path,
            token=self.token, notes=dict(notes or {}))


def write_private_manifest(result: LevelResult, private_root: str) -> str:
    os.makedirs(private_root, exist_ok=True)
    path = os.path.join(private_root, "%s.json" % result.task_id)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(result.private_manifest.to_json())
    return path
