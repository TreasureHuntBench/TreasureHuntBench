# World Format

A generated world is a directory:

```
<out_root>/
  github/<repo>/            local mirror of one repository
    repo.json               name, description, default branch, branches
    history.json            ordered commits with full file snapshots
                            (binary files base64-tagged as {"__b64__": ...})
    branches/<branch>/...   final working tree per branch
    issues.json releases.json
  cache/CACHE-*.json        external-source cache entries
  tasks/<task_id>/public_manifest.json
```

Private manifests (`<task_id>.json`) are written to a separate private root
and never inside the world tree.

## Clue-node artifact types

The private clue graph is a linear chain of typed nodes; the oracle solver
interprets them mechanically:

| type | location fields | meaning |
|---|---|---|
| `github_file` | repo, path, [branch] | read a file; observation must appear |
| `branch_doc` | repo, branch, path | same, branch required |
| `api_value` | source, query, rule | cached external value equals observation |
| `vtt_timestamp` | repo, path, timestamp | capture-cue lines at the second equal observation |
| `vtt_candidates` | list_repo, list_path, check_field, check_value, expected_path, timestamp | exactly one capture passes the NOTE-field check |
| `titles_list` | repo, path, last_n, method, shift | acrostic + stated decode equals observation |
| `github_repo_search` | pattern, check_path, check_field, check_value, [check2_*], expected_repo | exactly one candidate passes all checks |
| `git_history` | repo, before_message, path | payload in the last commit before the anchor |
| `csv_row` | repo, path, [branch], key | unique key row carries the observation |
| `zip_entry` | repo, path, [branch], arcname, password | entry content carries the observation |
| `terminal` | repo, path, [branch] | file whose single line is the final token |

## External sources

Approved sources (all cached, hashed, and cited at generation time):

- Open-Meteo historical weather (coldest-hour rules, earliest on ties)
- Yahoo Finance `GC=F` daily close, USD (approved gold-price source)
- ECB reference rates (Frankfurter API)
- World Bank Indicators
- Wikipedia REST page summaries / Wikidata entity labels

A bundled snapshot (`thb/sources/data/bundled.json`) keeps generation,
validation, and tests fully offline-reproducible.

## Capture artifacts (video-free profile)

Timed clues are WebVTT files committed to repositories: ``NOTE key=value``
header lines carry validation metadata (e.g. ``run_ref``), timed cues carry
the displayed fields. Upload logs (ordered JSON title lists) replace
playlist-order clues. The former YouTube node types (``youtube_timestamp``,
``youtube_candidates``, ``playlist_titles``) remain supported by the oracle
for video-backed worlds.
