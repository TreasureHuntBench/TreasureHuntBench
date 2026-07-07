from thb.core.naming import (
    NameForge, make_run_id, level_tag, nonce,
    contains_banned_phrase, is_banned_basename,
    BANNED_BASENAMES,
)
from thb.core.rng import TaskRng


def _forge(seed=11):
    rng = TaskRng(seed)
    run_id = make_run_id(4, 2, rng)
    return NameForge(run_id, rng), run_id


def test_run_id_shape_and_parts():
    _, run_id = _forge()
    assert run_id.startswith("L4S2-")
    assert level_tag(run_id) == "L4S2"
    assert len(nonce(run_id)) == 4


def test_deterministic_names():
    f1, _ = _forge(3)
    f2, _ = _forge(3)
    assert f1.repo_name(key=1348, label="a") == f2.repo_name(key=1348, label="a")
    assert f1.file_path("doc") == f2.file_path("doc")


def test_keyed_repo_name_contains_key():
    f, _ = _forge()
    assert "_1348_" in f.repo_name(key=1348, label="gold")


def test_paths_not_banned_and_task_specific():
    f, run_id = _forge()
    for label in ["a", "b", "c", "d"]:
        p = f.file_path(label)
        assert not is_banned_basename(p)
        assert level_tag(run_id) in p


def test_distinct_labels_distinct_paths():
    f, _ = _forge()
    assert f.file_path("x") != f.file_path("y")


def test_banned_phrase_detection():
    assert contains_banned_phrase("Here, The Clue Is simple") == "the clue is"
    assert contains_banned_phrase("Use the ledger row for 2018-04-17.") is None


def test_banned_basenames_detected():
    for b in BANNED_BASENAMES:
        assert is_banned_basename("some/dir/" + b.upper())


def test_start_path_uses_run_id():
    f, run_id = _forge()
    sp = f.start_path()
    assert sp.startswith("runbooks/")
    assert nonce(run_id) in sp
