import pytest

from thb.core.rng import TaskRng
from thb.gen.instructions import build_instruction_markdown, doc_title


STEPS = [
    ("use_gold_source", {}),
    ("get_gold_for_date", {"date": "2018-04-17"}),
    ("round_nearest_var", {"var": "GOLD_INT"}),
    ("open_repo_named", {"repo": "RXcTT_{GOLD_INT}_Q7"}),
    ("read_file", {"path": "records/RXcTT_{GOLD_INT}_Q7.md"}),
]


def test_document_structure_and_determinism():
    r = TaskRng(9)
    doc = build_instruction_markdown(r, "start", "L2S1", STEPS,
                                     front_matter={"run_id": "L2S1-8B1C"})
    assert doc == build_instruction_markdown(TaskRng(9), "start", "L2S1", STEPS,
                                             front_matter={"run_id": "L2S1-8B1C"})
    assert "run_id: L2S1-8B1C" in doc
    assert "1. " in doc and "5. " in doc
    assert "2018-04-17" in doc and "GOLD_INT" in doc


def test_languages():
    r = TaskRng(4)
    de = build_instruction_markdown(r, "x", "L6S3", STEPS, lang="de")
    ar = build_instruction_markdown(r, "x", "L6S3", STEPS, lang="ar")
    assert "Goldpreisquelle" in de
    assert "الذهب" in ar
    # values survive translation
    assert "2018-04-17" in de and "2018-04-17" in ar


def test_banned_phrase_guard():
    r = TaskRng(1)
    bad = [("read_file", {"path": "x.md — the clue is here"})]
    with pytest.raises(ValueError):
        build_instruction_markdown(r, "b", "L1S1", bad)


def test_title_varies_by_label_and_seed():
    r = TaskRng(2)
    assert doc_title(r, "a", "L1S1") != doc_title(r, "b", "L1S1")
    assert doc_title(TaskRng(2), "a", "L1S1") == doc_title(TaskRng(2), "a", "L1S1")
