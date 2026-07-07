# TreasureHuntBench — Atomic Commit List

Each commit is implemented, tested, then committed and pushed before moving to
the next. Checkboxes are updated as commits land.

- [x] **C01 — Repository scaffolding.** `.gitignore` (credentials + `private/`
  excluded), `README.md`, `IMPLEMENTATION_PLAN.md`, `commit_list.md`,
  `pyproject.toml`/`setup.cfg`, `thb` package skeleton with empty subpackages,
  pytest wiring, spec document. Verify: `pip install -e .` and `pytest` run.

- [ ] **C02 — Deterministic RNG + token minting.** `thb/core/rng.py`
  (`TaskRng`: named substreams, stable across runs), `thb/core/tokens.py`
  (mint `THB{...}` tokens, sha256 hashing, verification helper). Tests:
  same seed → same values; different names → independent streams; token
  verify round-trip.

- [ ] **C03 — Anti-leakage naming generator.** `thb/core/naming.py`: run-ids,
  repo names, file paths derived from family/step/values; banned-name and
  banned-phrase lists exported for the leakage scanner. Tests: determinism,
  no banned names, uniqueness across steps.

- [ ] **C04 — Core schemas + source cache.** `thb/core/schemas.py`
  (ClueNode, WorldArtifact, SkillDef, PublicManifest, PrivateManifest,
  CacheEntry, TraceEvent, Trace — all JSON-serializable),
  `thb/core/cache.py` (SourceCache: put/get, raw-response sha256, citation
  records, deterministic cache ids). Tests: round-trip serialization, hash
  stability, cache hit/miss.

- [ ] **C05 — External source modules.** `thb/sources/`: base interface +
  Open-Meteo, gold price, FRED, Wikipedia/Wikidata, World Bank; each exposes
  `fetch/normalize/cite/cache`; bundled offline fallback data
  (`thb/sources/data/`) so generation and tests work without network; helpers
  `get_coldest_hour`, `get_gold_price`, `get_series_observation`. Tests run
  offline against bundled data.

- [ ] **C06 — File/database/archive/encoding artifact generators.**
  `thb/artifacts/`: realistic markdown/json/csv writers, SQLite generator,
  ZIP (incl. password) generator, encoding codecs (base64, hex, caesar,
  vigenère, morse, acrostic), multilingual (EN/DE/AR) instruction renderer.
  Tests: every codec round-trips; archives extract; AR/DE render values
  verbatim.

- [ ] **C07 — World/clue/skill graph builders.** `thb/graphs/`: build, link,
  serialize the three private graphs; skill cards; graph integrity checks
  (single path, no orphan clue nodes, skill dependencies resolvable). Tests.

- [ ] **C08 — Instruction generator.** `thb/gen/instructions.py`: direct
  operational instruction text from clue nodes, with verb/structure variation
  but full determinism per seed; renders EN/DE/AR via multilingual module.
  Tests: all required fields present, no banned boilerplate phrases.

- [ ] **C09 — Decoy generator.** `thb/gen/decoys.py`: near-duplicate repos,
  wrong run_ref / inactive-state / wrong-date / wrong-shift decoys, each
  invalid under an explicit stated rule; decoy manifest entries. Tests: decoys
  always violate their stated rule; never contain the real token.

- [ ] **C10 — GitHub publisher.** `thb/gen/github_pub.py`: create/update org
  repos, branches, commits (incl. history construction), issues, tags,
  releases via the GitHub REST API (token from `gh auth token`); dry-run mode
  writes the same tree locally. Tests: dry-run tree correctness; live smoke
  test against one scratch repo in the org.

- [ ] **C11 — YouTube artifact generator.** `thb/gen/youtube_pub.py`: timed
  text frames (Pillow), `.vtt` captions, metadata json, playlist manifests,
  local mirror layout; mp4 assembly when ffmpeg is present; optional unlisted
  upload path using local OAuth credentials (never committed). Tests: mirror
  contains correct text at the correct timestamp; captions parse.

- [ ] **C12 — Family 1: Basic Clue Following.** Generator + oracle route +
  tests (oracle recovers token; validators pass; grep baseline fails).

- [ ] **C13 — Family 2: Real-Website Navigation** (wiki-based intermediate
  values, introduces `get_gold_price` skill card). Same test contract.

- [ ] **C14 — Family 3: API-Based Historical Data** (Open-Meteo coldest hour →
  video timestamp; introduces `get_coldest_hour`). Same test contract.

- [ ] **C15 — Family 4: Multi-Repository Search** (near-duplicate repos,
  run_id filtering; introduces `search_and_filter_repositories`). Same test
  contract.

- [ ] **C16 — Family 5: YouTube Timestamp Clues** (introduces
  `timestamped_video_clue_extraction`). Same test contract.

- [ ] **C17 — Family 6: Multilingual Clues** (DE/AR operational documents;
  introduces `cross_lingual_clue_following`). Same test contract.

- [ ] **C18 — Family 7: Encoded Messages** (playlist acrostic + caesar etc.;
  introduces `decode_explicit_hidden_messages`). Same test contract.

- [ ] **C19 — Family 8: Memory & Skill Transfer** (symbol mappings stored in
  one sub-level, required in later ones; introduces
  `persistent_skill_memory`). Same test contract.

- [ ] **C20 — Family 9: Decoys & Verification** (run_ref/artifact_state
  validation, injection text in invalid artifacts; introduces
  `verify_before_following`). Same test contract.

- [ ] **C21 — Family 10: Grand Multi-Source Hunt** (composes all prior skills
  across weather → video → market key → repo filtering → git history →
  decoding → CSV → ZIP → AR document → token). Same test contract.

- [ ] **C22 — Validators.** `thb/validate/`: oracle solver (mechanical clue
  graph walker over local world + cache), leakage scanner (banned phrases,
  banned filenames, token exposure, grep-shortcut simulation, private-file
  exposure), one-answer validator (unique candidate/path/token, tie-break
  audit). Tests incl. deliberately broken levels being rejected.

- [ ] **C23 — Evaluator.** `thb/eval/`: trace schema/auditor and all scorers
  (final token, partial progress, skill reuse, memory, source accuracy,
  citation, robustness, efficiency, trace plausibility); JSON score report.
  Tests: oracle trace scores ~perfect; corrupted traces lose the right
  points.

- [ ] **C24 — Baselines.** grep baseline, search-only baseline, oracle agent;
  runner that reports per-level success. Tests: on generated worlds grep and
  search-only fail, oracle succeeds.

- [ ] **C25 — CLI.** `thb` entrypoint: `generate`, `validate`, `publish`,
  `solve`, `evaluate`, `baseline`. Tests: CLI smoke tests on a tiny world.

- [ ] **C26 — End-to-end suite.** One test that generates a mini-world with
  every family, validates all levels, solves with oracle, evaluates traces,
  runs baselines, and checks the QC checklist programmatically.

- [ ] **C27 — Documentation.** `docs/`: getting started, world format, task
  manifests, trace format, scoring, split policy, security rules, dataset
  card skeleton.

- [ ] **C28 — Benchmark generation.** Generate the MVP benchmark locally:
  training/validation/test splits across families with per-split policies
  (public answers for training; hidden manifests under `private/` for
  val/test); run all validators; write split index files.

- [ ] **C29 — Publication.** Publish training-split level repos to the
  TreasureHuntBench GitHub org (plus validation starting artifacts), verify
  live, write `worlds/INDEX.md` and final status report.
