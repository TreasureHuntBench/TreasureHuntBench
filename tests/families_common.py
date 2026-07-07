"""Shared test contract for every level family."""
import re

from thb.core.naming import contains_banned_phrase, is_banned_basename
from thb.core.tokens import token_hash
from thb.gen.github_pub import LocalMirrorPublisher


def walk_public_texts(out_root):
    """Yield (path, text) for every public text artifact in a world."""
    import os
    for base, _dirs, files in os.walk(out_root):
        for name in files:
            full = os.path.join(base, name)
            try:
                with open(full, encoding="utf-8") as fh:
                    yield full, fh.read()
            except (UnicodeDecodeError, OSError):
                continue


def assert_family_contract(result, out_root):
    """Common assertions every generated sub-level must satisfy."""
    token = result.token
    assert result.private_manifest.final_token_hash == token_hash(token)

    # 1. clue chain is coherent and ends at a terminal node
    nodes = result.private_manifest.clue_nodes()
    assert nodes[-1].artifact_type == "terminal"

    # 2. the token appears in exactly one public artifact: the terminal file
    github = LocalMirrorPublisher(out_root)
    terminal = nodes[-1]
    branch = terminal.location.get("branch", "main")
    terminal_rel = "github/%s/branches/%s/%s" % (
        terminal.location["repo"], branch, terminal.location["path"])
    hits = []
    for path, text in walk_public_texts(out_root):
        if token in text:
            hits.append(path.replace("\\", "/"))
    public_hits = [h for h in hits if "/tasks/" not in h]
    # history.json legitimately snapshots the terminal file's repo history
    non_history = [h for h in public_hits if not h.endswith("history.json")]
    assert non_history, "token not reachable in world"
    for hit in non_history:
        assert hit.endswith(terminal_rel), "token leaked to %s" % hit
    for hit in [h for h in public_hits if h.endswith("history.json")]:
        assert ("github/%s/" % terminal.location["repo"]) in hit, \
            "token leaked into another repo's history: %s" % hit

    # 3. no banned phrases or basenames anywhere public
    for path, text in walk_public_texts(out_root):
        if "/tasks/" in path.replace("\\", "/"):
            continue
        hit = contains_banned_phrase(text)
        assert hit is None, "banned phrase %r in %s" % (hit, path)
        assert not is_banned_basename(path)

    # 4. decoys all carry explicit invalid rules
    for art in result.private_manifest.artifacts():
        if art.decoy_status == "decoy":
            assert art.invalid_rule

    # 5. public manifest exists and never contains the token or its hash
    pm = result.public_manifest.to_json()
    assert token not in pm and token_hash(token) not in pm


def grep_baseline_fails(result, out_root):
    """A regex sweep for clue boilerplate must not find the token path."""
    patterns = [r"next[ _]clue", r"final[ _]answer", r"the clue is",
                r"treasure", r"secret"]
    for path, text in walk_public_texts(out_root):
        if "/tasks/" in path.replace("\\", "/"):
            continue
        # the organization/channel name is legitimate world furniture
        scrubbed = re.sub(r"treasurehuntbench", "", text, flags=re.IGNORECASE)
        for pat in patterns:
            assert not re.search(pat, scrubbed, re.IGNORECASE), \
                "grep shortcut %r works on %s" % (pat, path)
