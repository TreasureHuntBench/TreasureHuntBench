"""Final-token minting and verification.

Final treasure tokens have the form ``THB{<body>}`` where the body is a
seed-derived, non-searchable random string. Evaluator-side storage keeps only
``sha256(token)`` so a leaked private manifest never reveals the token itself.
"""

import hashlib
import string

from .rng import TaskRng

_BODY_ALPHABET = string.ascii_letters + string.digits

TOKEN_PREFIX = "THB{"
TOKEN_SUFFIX = "}"
ANSWER_FORMAT = "THB{...}"


def mint_token(rng: TaskRng, run_id: str, length: int = 24) -> str:
    """Mint the unique final token for a task, deterministic per seed."""
    body = rng.code("final_token:" + run_id, length, _BODY_ALPHABET)
    return TOKEN_PREFIX + body + TOKEN_SUFFIX


def token_hash(token: str) -> str:
    return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(submission: str, stored_hash: str) -> bool:
    """Check a submitted answer against the stored hash (exact match only)."""
    return token_hash(submission.strip()) == stored_hash


def looks_like_token(text: str) -> bool:
    return text.startswith(TOKEN_PREFIX) and text.endswith(TOKEN_SUFFIX)
