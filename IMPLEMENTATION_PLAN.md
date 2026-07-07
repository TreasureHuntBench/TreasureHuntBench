# TreasureHuntBench — Implementation Plan

This document describes how the TreasureHuntBench system is implemented, in what
order, and how each part is verified. The full benchmark specification lives in
`TreasureHuntBenchDescription.md`; this plan is the engineering roadmap for it.

## 1. Goals

Build a working, end-to-end system that:

1. **Generates** synthetic, deterministic, multi-source treasure-hunt levels
   (world graph + clue graph + skill graph) across ten level families.
2. **Publishes** the visible world: GitHub repositories under the
   `TreasureHuntBench` organization, unlisted YouTube artifacts (with local
   mirrors), and generated local files (Markdown, JSON, CSV, SQLite, ZIP,
   multilingual documents).
3. **Validates** every generated level with an oracle solver, a leakage
   scanner, and a one-answer validator before release.
4. **Evaluates** agent submissions: final token, partial progress, skill
   reuse, memory, source accuracy, citations, robustness, efficiency, and
   trace plausibility.
5. Ships **baselines** (grep, search-only, oracle) that prove levels cannot be
   shortcut-solved.

## 2. Architecture

One Python package, `thb/`, plus generated data directories.

```
thb/
  core/
    rng.py            deterministic seeded RNG (single source of randomness)
    naming.py         anti-leakage task-specific name generator
    schemas.py        dataclasses: manifests, graphs, cache entries, traces
    cache.py          external-source cache: query, raw hash, normalization,
                      citation, retrieval timestamp
    tokens.py         final-token minting + hashing (sha256 only stored)
  sources/
    base.py           ExternalSource interface: fetch/normalize/cite/cache
    open_meteo.py     historical weather (coldest hour etc.)
    gold.py           approved gold-price source (cached USD PM fixing)
    fred.py           FRED series observations
    wiki.py           Wikipedia REST + Wikidata SPARQL/entity API
    worldbank.py      World Bank indicators
  artifacts/
    files.py          markdown/json/csv writers with realistic framing
    sqlite_gen.py     SQLite database artifacts
    archive.py        ZIP archives (optionally password-protected)
    encodings.py      base64/hex/caesar/vigenere/morse/acrostic codecs
    multilingual.py   EN/DE/AR operational-instruction rendering
  graphs/
    world.py          world graph builder (artifacts + decoys)
    clue.py           clue graph builder (intended path, validation rules)
    skills.py         skill graph + skill cards (introduce/practice/require)
  gen/
    instructions.py   direct, deterministic instruction text generator
    decoys.py         rule-invalid decoy generator
    github_pub.py     GitHub publisher (repos/branches/commits/issues/releases)
    youtube_pub.py    YouTube artifact synthesis (frames via Pillow, captions,
                      metadata) + local mirror; unlisted upload when OAuth
                      token is available, mirror-only otherwise
  families/
    f01_basic.py … f10_grand.py   one generator per level family
    registry.py       family registry + shared level-assembly helpers
  validate/
    oracle.py         oracle solver walks the private clue graph mechanically
    leakage.py        leakage scanner (boilerplate phrases, predictable names,
                      token exposure, grep-shortcut simulation)
    one_answer.py     uniqueness checks (single valid candidate/path/token)
  eval/
    scoring.py        final token, partial progress, skill reuse, memory,
                      source accuracy, citation, robustness, efficiency
    trace.py          trace schema + trace auditor
  baselines/
    grep_baseline.py  regex/grep shortcut attempt (must fail)
    search_only.py    search-without-path attempt (must fail)
    oracle_agent.py   follows private graph (must succeed)
  cli.py              `thb generate | validate | publish | evaluate | solve`
tests/                pytest suite, one module per subsystem + e2e
docs/                 benchmark documentation
worlds/               generated public artifacts per world (committed for
                      training split); private manifests go to private/ (never
                      committed)
```

### Key design decisions

- **Determinism**: every level is a pure function of `(family, seed)`. All
  randomness flows through `thb.core.rng.TaskRng` (a named, seeded PRNG).
  Regenerating with the same seed reproduces the identical world byte-for-byte
  (modulo external publish timestamps).
- **Offline-first external data**: every external value used for scoring is
  fetched once, cached under `worlds/<id>/cache/` with its raw-response hash,
  query, normalization rule, and citation. The oracle and evaluator only read
  the cache; live APIs are used only at generation time. A small bundled
  fallback dataset (gold fixings, weather extracts) keeps generation and tests
  working without network access.
- **Publish is a separate phase**: generation writes a complete local world
  tree; `thb publish` pushes GitHub repos / uploads videos afterwards. This
  keeps generation testable and lets validators run before anything is public.
- **Private/public split enforced by paths**: everything under `private/` is
  gitignored; the leakage scanner additionally greps staged public trees for
  final tokens, private-manifest fields, and clue boilerplate before publish.
- **Anti-leakage naming**: `naming.py` derives artifact names from the task
  run-id, family, and step values (e.g. `records/L4S2_83A_route.md`,
  `RXcTT_1348_Q7`), never generic names, and the leakage scanner rejects a
  banned-phrase/banned-filename list globally.
- **YouTube realism without hard dependency**: the video generator renders
  timed text frames (Pillow) and caption files (`.vtt`), assembles an mp4 when
  `ffmpeg` exists, and always writes a local mirror
  (`worlds/<id>/media_mirror/...`) that the harness and oracle use. Uploading
  as unlisted via the Data API is a publish-time option using local OAuth
  credentials (never committed).

## 3. Level assembly model

Every sub-level is assembled from the same primitives:

1. Pick a **run id** (e.g. `L5S1-7C3`) and mint a **final token**
   `THB{...}` (private; only its sha256 is stored).
2. Build the **clue chain**: a list of `ClueNode`s, each with artifact type,
   location, required tool, expected observation, deterministic normalization,
   validation condition, and pointer to the next node.
3. Materialize **artifacts** for each node (files, repos, videos), plus
   **decoys** that are invalid under an explicit rule (wrong `run_ref`,
   `artifact_state: inactive`, wrong date…).
4. Emit the **public manifest** (start artifact, allowed tools, approved
   sources, answer format, budgets) and the **private manifest** (seed,
   graphs, oracle trace, token hash, decoy list, cache refs).
5. Run the three validators; a level that fails any validator is rejected.

## 4. Verification strategy

- Unit tests per module (pytest), run before every commit.
- Every family generator is tested by: generate a level → run oracle solver →
  assert it recovers exactly the minted token → run leakage scanner and
  one-answer validator → assert pass; run grep baseline → assert fail.
- End-to-end test: generate a small world containing every family, validate
  all, evaluate the oracle trace, check scoring output shape.
- Publish steps verified against the live GitHub org (`gh api`) after pushing.

## 5. Delivery phases (mapped to commits)

See `commit_list.md` for the atomic commit breakdown. Order:

1. Scaffolding → 2. core (rng/naming/schemas/cache/tokens) → 3. sources →
4. artifacts → 5. graphs → 6. instructions+decoys → 7. publishers →
8. families 1–10 → 9. validators → 10. evaluator → 11. baselines → 12. CLI →
13. e2e tests → 14. docs → 15. benchmark generation + publication to the org.

## 6. Security and hygiene rules

- `yt_api_key.json`, OAuth tokens, and any credentials are gitignored and
  never read into generated artifacts.
- `private/` (seeds, graphs, token hashes, oracle traces, caches for hidden
  splits) is never committed to public repos.
- Published level repos contain only public-manifest-visible content.
- Final tokens never appear in any public artifact except the single intended
  terminal file of the intended path.
