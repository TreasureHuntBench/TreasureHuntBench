# Getting Started

## Install

```bash
pip install -e .
pytest            # full test suite, runs offline
```

## Generate a world

```bash
thb generate --family all --seed 42 \
    --out worlds/dev --private private/dev --world-id W-DEV
```

This builds every level family (11 sub-levels), validates each level with
the oracle solver, leakage scanner, and one-answer validator, writes public
artifacts under `worlds/dev/` and private manifests under `private/dev/`.

Generate a single family instead with `--family 4`. Families 8.2 and 10
depend on world memory from family 8.1, so they are only available through
`--family all` (the world plan runs in dependency-safe order).

## Inspect and solve

```bash
thb validate --out worlds/dev --private private/dev
thb solve --out worlds/dev --private private/dev --task THB-TR-L4S1-XXXX
thb baseline --which grep   --out worlds/dev          # must NOT solve
thb baseline --which oracle --out worlds/dev \
    --private private/dev --task THB-TR-L4S1-XXXX     # must solve
```

## Score a submission

```bash
thb evaluate --trace my_trace.json --private private/dev
```

The trace format is documented in `docs/trace_format.md`.

## Publish to GitHub

```bash
thb publish --out worlds/dev --dry-run    # list what would be pushed
thb publish --out worlds/dev              # create repos in the org
```

Publishing requires `gh` authenticated with `repo` + `admin:org` scopes and
SSH access to `github.com:TreasureHuntBench`.
