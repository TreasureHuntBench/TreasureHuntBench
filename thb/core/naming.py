"""Anti-leakage naming for generated artifacts.

All repository names, branch names, and file paths in generated worlds are
derived from the task run-id, the level family, and step-specific values.
Nothing is ever called ``clue.md`` or ``answer.md``, and instruction text is
assembled elsewhere without global boilerplate phrases. The banned lists
below are the single source of truth also used by the leakage scanner.
"""

from typing import Optional

from .rng import TaskRng

# Phrases that must never appear in public artifacts (case-insensitive).
# An agent should never be able to grep for a global phrase to jump ahead.
BANNED_PHRASES = [
    "the clue is",
    "next clue",
    "next step",
    "final answer",
    "treasure is",
    "hidden clue",
    "secret message",
    "validation-marker",
    "valid-clue",
    "decoy-clue",
    "submit this",
    "the answer is",
]

# Basenames that must never be used for generated artifacts.
BANNED_BASENAMES = [
    "next_step.md",
    "clue.md",
    "clues.md",
    "answer.md",
    "answers.md",
    "final.txt",
    "final.md",
    "solution.md",
    "secret.md",
    "treasure.md",
    "treasure.txt",
]

# Realistic directory vocabularies, rotated deterministically per task.
_DIR_POOLS = [
    "records", "reports", "docs", "archive", "manifests", "runbooks",
    "packets", "tables", "media", "ledgers", "language_pack", "candidates",
    "registry", "exports", "bundles", "notes",
]

_REPO_STEMS = [
    "RXcTT", "thb", "kestrel", "morrow", "quarry", "halcyon", "vantage",
    "ledgerworks", "atlaskeep", "signalbay",
]


def make_run_id(family_num: int, sub_num: int, rng: TaskRng) -> str:
    """Task-specific run id, e.g. 'L4S2-7QK9'."""
    return "L%dS%d-%s" % (family_num, sub_num, rng.code("run_id", 4))


def level_tag(run_id: str) -> str:
    """'L4S2-7QK9' -> 'L4S2'."""
    return run_id.split("-", 1)[0]


def nonce(run_id: str) -> str:
    """'L4S2-7QK9' -> '7QK9'."""
    return run_id.split("-", 1)[1]


class NameForge:
    """Deterministic artifact-name factory for one task."""

    def __init__(self, run_id: str, rng: TaskRng):
        self.run_id = run_id
        self.rng = rng
        self._counter = 0

    def _dir(self, label: str) -> str:
        return self.rng.choice("dir:" + label, _DIR_POOLS)

    def repo_stem(self) -> str:
        return self.rng.choice("repo_stem", _REPO_STEMS)

    def repo_name(self, key: Optional[object] = None, label: str = "") -> str:
        """Repository name, optionally keyed by a derived value.

        With key: '<stem>_<key>_<code>' (e.g. RXcTT_1348_Q7) — the pattern
        used when the agent must compute the key from an external source.
        Without key: '<stem>-<leveltag>-<code>' (e.g. thb-L4S2-K3M1).
        """
        code = self.rng.code("repo_code:%s:%s" % (label, key), 2)
        if key is not None:
            return "%s_%s_%s" % (self.repo_stem(), key, code)
        return "%s-%s-%s" % (self.repo_stem(), level_tag(self.run_id),
                             self.rng.code("repo_code2:" + label, 4))

    def branch_name(self, key: object, label: str = "") -> str:
        word = self.rng.choice(
            "branch_word:" + label,
            ["archive", "archiv", "rollout", "ingest", "batch", "series"])
        return "%s-%s" % (word, key)

    def file_path(self, label: str, ext: str = "md",
                  key: Optional[object] = None) -> str:
        """Task-specific path, e.g. 'records/L4S2_83A_route.md'."""
        directory = self._dir(label)
        code = self.rng.code("file_code:" + label, 3)
        stem_words = ["route", "review", "ledger", "bundle", "index",
                      "event", "ref", "log", "brief", "survey"]
        word = self.rng.choice("file_word:" + label, stem_words)
        parts = [level_tag(self.run_id), code]
        if key is not None:
            parts.append(str(key))
        parts.append(word)
        name = "%s.%s" % ("_".join(str(p) for p in parts), ext)
        assert name not in BANNED_BASENAMES
        return "%s/%s" % (directory, name)

    def manifest_path(self, repo_name: str) -> str:
        return "manifests/%s.json" % repo_name

    def start_path(self) -> str:
        return "runbooks/%s_start_%s.md" % (
            level_tag(self.run_id), nonce(self.run_id))


def contains_banned_phrase(text: str) -> Optional[str]:
    low = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            return phrase
    return None


def is_banned_basename(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].lower()
    return base in BANNED_BASENAMES
