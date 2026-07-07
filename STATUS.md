# TreasureHuntBench — Build Status

## System

Complete and tested (100 pytest tests, all green, fully offline):

- **Core**: deterministic seeded RNG with named substreams; `THB{...}`
  token minting (only sha256 stored evaluator-side); anti-leakage naming
  with banned phrase/basename lists; JSON schemas for manifests, graphs,
  cache entries, traces; hashed + cited external-source cache.
- **External sources** (all with offline snapshots): Open-Meteo historical
  weather, Yahoo Finance GC=F gold close (approved gold source), ECB
  reference rates, World Bank indicators, Wikipedia/Wikidata.
- **Artifacts**: markdown/JSON/CSV writers, SQLite, AES-password ZIPs,
  six reversible codecs, EN/DE/AR operational instruction templates.
- **Publishers**: GitHub (local mirror with full per-commit history +
  live org publishing over SSH/REST, binary-safe). Timed clues use in-repo
  WebVTT capture artifacts and upload logs (video-free profile); a YouTube
  generator (frame cards, captions, mirrors, unlisted-upload path) is
  retained for a future video-backed profile.
- **Level families 1–10** per the specification, including near-duplicate
  repository decoys, prompt-injection bait with fake tokens, per-world
  rotated memory vocabularies, git-history payloads scrubbed at head, and
  the full Grand Multi-Source Hunt composition.
- **Validators**: oracle solver (mechanical clue-graph walker), leakage
  scanner, one-answer validator — every released level passes all three.
- **Evaluator**: trace auditor + eight metrics with weighted composite;
  answers without path evidence are capped and flagged.
- **Baselines**: grep (fails by construction — every level plants a fake
  token-shaped string), search-only (fails), oracle agent (succeeds).
- **CLI**: `thb generate | validate | solve | evaluate | baseline | publish`.

## Benchmark (MVP)

| split | worlds | tasks | answers | published |
|---|---|---|---|---|
| training | 3 (seeds 1001–1003) | 33 | released (`benchmark/training/answers.json`, incl. oracle traces) | full worlds + cache assets repos |
| validation | 2 (seeds 2001–2002) | 22 | hidden | full worlds + cache assets repos |
| test | 2 (seeds 3001–3002) | 22 | hidden | not published (held privately) |

Published artifacts live in the
[TreasureHuntBench organization](https://github.com/TreasureHuntBench);
see `worlds/INDEX.md` for the verified repository list. Each world also has
a `thb-assets-<split>-<world>` repository carrying the public source cache
(cited, hashed external observations used by the tasks).

## Known limitations / next steps

- The benchmark currently runs the **video-free profile**: timed clues are
  in-repo WebVTT captures and upload logs. The YouTube pipeline
  (generation, mirrors, unlisted upload) exists and can back a future
  video profile once OAuth is authorized and upload quota is arranged
  (default API quota allows only ~6 uploads/day).
- Test-split scoring infrastructure (submission endpoint, leaderboard) is
  future work; the evaluator and trace auditor are in place.
- ReAct / plan-and-execute / memory-augmented LLM baselines are stubs for
  future work; grep, search-only, and oracle baselines are implemented.
