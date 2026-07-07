# Scoring and Trace Format

## Trace format

A submission is a JSON `Trace`:

```json
{
  "task_id": "THB-VAL-L5S1-7C3K",
  "agent_id": "my-agent",
  "model_id": "my-model",
  "final_submission": "THB{...}",
  "events": [
    {"tool": "github.read_file",
     "target": "TreasureHuntBench/<repo>/runbooks/L5S1_start_7C3K.md"},
    {"tool": "api.Open-Meteo Historical Weather API",
     "query": {"city": "Passau, Germany", "date": "2017-01-12",
               "timezone": "Europe/Berlin"},
     "normalized_value": "03",
     "citation": "Open-Meteo Historical Weather API"},
    {"tool": "youtube.inspect", "target": "video_L5S1_XXX",
     "query": {"timestamp": "00:03"},
     "extracted": {"lines": ["repository=...", "document=..."]}}
  ]
}
```

Event fields: `tool` (required), `target`, `query`, `extracted`,
`normalized_value`, `citation`, `note`.

Tool-name prefixes matter to the auditor: `github*`/`file*` for repository
and file reads, `api*` for external sources, `youtube*` for videos and
playlists, `archive*` for ZIP entries.

## Metrics

All in [0, 1]; composite is a weighted sum (weights in
`thb/eval/scoring.py`):

| metric | meaning |
|---|---|
| final_token_success | exact sha256 match of the submission |
| partial_clue_progress | fraction of private clue nodes evidenced in the trace |
| skill_reuse_score | skill-tagged nodes evidenced |
| source_accuracy_score | api values in the trace match the cached observations |
| citation_quality_score | api events carrying citations |
| robustness_score | penalties for fake-token submissions and followed decoys |
| efficiency_score | intended steps / trace events (capped at 1) |
| trace_plausibility_score | in-order coverage; capped at 0.2 when the answer has no path evidence |

Trace auditing flags correct answers that never visited the terminal
artifact or show no evidenced path steps — a leaked/guessed token scores
`final_token_success = 1` but is capped everywhere else and flagged in
`audit.issues` for manual review.

## One-answer guarantee

Every released level passes three validators:

1. **Oracle solver** — mechanically recovers exactly the minted token.
2. **Leakage scanner** — no banned phrases, no predictable filenames, no
   token outside the intended terminal artifact, no private fields in
   public trees, no grep-shortcut matches.
3. **One-answer validator** — one terminal node, cache-backed external
   values, unique candidate at every filtering step, no decoy containing
   the real token.
