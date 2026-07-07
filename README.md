# TreasureHuntBench

**TreasureHuntBench** is a synthetic, realistic, multi-level benchmark for
evaluating long-horizon LLM agents and agentic frameworks.

Agents wander a simulated information world — GitHub repositories, unlisted
YouTube videos, Wikipedia/Wikidata, historical weather and financial APIs,
generated documents, databases, and archives — following deterministic clue
chains, learning reusable skills, managing memory, avoiding decoys and
prompt-injection traps, citing evidence, and finally recovering exactly one
synthetic treasure token per level.

- Official GitHub organization: [`TreasureHuntBench`](https://github.com/TreasureHuntBench)
- Official YouTube account: `@TreasureHuntBench`

## What's here

| Path | Contents |
|---|---|
| `thb/` | Benchmark system: generators, publishers, validators, evaluator, baselines, CLI |
| `tests/` | Test suite (100 tests, runs offline) |
| `docs/` | Benchmark documentation |
| `benchmark/` | The MVP benchmark: task indexes, public manifests, training answers + oracle traces |
| `worlds/INDEX.md` | Verified list of the 135 published world repositories |
| `scripts/` | Benchmark generation and publication scripts |
| `STATUS.md` | Build status, split table, known limitations |
| `TreasureHuntBenchDescription.md` | Full benchmark specification |
| `IMPLEMENTATION_PLAN.md` | Engineering plan |
| `commit_list.md` | Atomic commit roadmap |

The MVP benchmark is live: **77 tasks** (33 training with released answers,
22 validation, 22 test held privately) across **7 generated worlds**, with
**135 repositories** published to this organization.

## Quick start

```bash
pip install -e .
pytest

# generate a level, validate it, solve it with the oracle
thb generate --family 1 --seed 42 --out worlds/dev
thb validate worlds/dev
thb solve worlds/dev
```

## Core guarantees

- **Exactly one answer per level** — enforced by a one-answer validator.
- **Deterministic** — every level is a pure function of `(family, seed)`.
- **Reproducible** — every external value used in scoring is cached, hashed,
  and cited; scoring never depends on live data.
- **Shortcut-resistant** — a leakage scanner bans searchable clue boilerplate
  and predictable filenames; grep/search-only baselines must fail.
- **Private answers** — evaluators store only `sha256(final_token)`; private
  manifests are never published.

## Security

Credentials (`yt_api_key.json`, OAuth tokens) and everything under `private/`
are gitignored and must never be committed or embedded in generated artifacts.
