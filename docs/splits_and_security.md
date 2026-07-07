# Splits and Security

## Split policy

| | Training | Validation | Test |
|---|---|---|---|
| GitHub repos | public | public start artifacts | controlled |
| YouTube videos | public or unlisted | unlisted | private/unlisted + mirrors |
| Answers | released | hidden | hidden |
| Seeds & clue graphs | released | hidden | hidden |
| Scoring | self-serve | official evaluator | external, trace-audited |
| External values | cached | cached | cached |

Task ids encode the split: `THB-TR-*`, `THB-VAL-*`, `THB-TEST-*`.

Validation/Test scoring always uses the generation-time source cache —
never live APIs — so tasks stay reproducible even if the live sources
change.

## Security rules

1. Credentials (`yt_api_key.json`, OAuth tokens, `client_secret*.json`)
   are gitignored and must never be committed or embedded in artifacts.
2. Everything under `private/` (seeds, graphs, oracle traces, token hashes,
   hidden-split caches) is never pushed to public repositories.
3. Evaluator-side storage keeps only `sha256(final_token)`.
4. Unlisted YouTube videos reduce leakage but do not eliminate it; they are
   always combined with private manifests, answer hashes, and trace
   auditing.
5. Published level repositories contain only what the public manifest
   declares visible.

## Dataset card (skeleton)

- **Name**: TreasureHuntBench
- **Purpose**: evaluating long-horizon, multi-source, tool-using LLM agents
  (clue following, skill learning/transfer, memory, decoy resistance,
  citation).
- **Composition**: synthetic worlds of GitHub repositories, unlisted
  YouTube artifacts (locally mirrored), cached real-world API observations
  (weather, gold, FX, World Bank, Wikipedia/Wikidata), generated documents,
  databases, and archives, in English, German, and Arabic.
- **Answer policy**: exactly one synthetic `THB{...}` token per level;
  external sources provide intermediate values only.
- **Contamination controls**: seed-deterministic regeneration, hidden
  seeds/manifests for validation/test, banned-boilerplate scanning, token
  noise against pattern sweeps, trace plausibility auditing.
- **Licenses**: external observations are cached with source citations;
  see each source's terms for redistribution constraints.
