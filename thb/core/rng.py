"""Deterministic seeded randomness for TreasureHuntBench.

Every piece of randomness in the benchmark flows through :class:`TaskRng`.
A ``TaskRng`` is created from a world/level seed and hands out *named
substreams*: independent, reproducible PRNG streams keyed by a string label.
Regenerating a level with the same seed therefore reproduces the identical
world regardless of the order in which subsystems draw values.
"""

import hashlib
import random
import string
from typing import List, Sequence, TypeVar

T = TypeVar("T")

_ALNUM_UPPER = string.ascii_uppercase + string.digits
_HEXISH = "0123456789ABCDEF"


def _derive_seed(seed: int, name: str) -> int:
    digest = hashlib.sha256(("%d:%s" % (seed, name)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class TaskRng:
    """Root deterministic RNG for one generated task/world."""

    def __init__(self, seed: int):
        self.seed = int(seed)

    def stream(self, name: str) -> random.Random:
        """Return an independent PRNG for the named substream.

        The same (seed, name) pair always yields a generator producing the
        same sequence; different names are statistically independent.
        """
        return random.Random(_derive_seed(self.seed, name))

    # -- convenience draws (each uses its own one-shot substream so the
    # -- result depends only on (seed, name), never on call order) ------

    def randint(self, name: str, low: int, high: int) -> int:
        return self.stream(name).randint(low, high)

    def choice(self, name: str, options: Sequence[T]) -> T:
        return self.stream(name).choice(list(options))

    def sample(self, name: str, options: Sequence[T], k: int) -> List[T]:
        return self.stream(name).sample(list(options), k)

    def shuffle(self, name: str, options: Sequence[T]) -> List[T]:
        items = list(options)
        self.stream(name).shuffle(items)
        return items

    def code(self, name: str, length: int = 4, alphabet: str = _ALNUM_UPPER) -> str:
        """Short uppercase alphanumeric code, e.g. '7QK9'."""
        rng = self.stream(name)
        return "".join(rng.choice(alphabet) for _ in range(length))

    def hexish(self, name: str, length: int = 4) -> str:
        """Hex-looking uppercase code, e.g. '8F3C'."""
        return self.code(name, length, _HEXISH)

    def child(self, name: str) -> "TaskRng":
        """Derive a child TaskRng (e.g. one per sub-level)."""
        return TaskRng(_derive_seed(self.seed, "child:" + name))
