import pytest

from thb.core.rng import TaskRng
from thb.core.tokens import mint_token
from thb.gen.decoys import (decoy_state_fields, fake_token, injection_text,
                            near_duplicate_keys, perturb_ref, stale_note)


def test_fake_token_differs_from_real():
    r = TaskRng(3)
    real = mint_token(r, "L9S3-2D8A")
    fake = fake_token(r, "video1", real)
    assert fake != real and fake.startswith("THB{") and fake.endswith("}")
    assert fake == fake_token(TaskRng(3), "video1", real)  # deterministic


def test_perturb_ref_one_char():
    r = TaskRng(5)
    ref = "L9S3-2D8A"
    bad = perturb_ref(r, ref, "m1")
    assert bad != ref and len(bad) == len(ref)
    diffs = [i for i, (a, b) in enumerate(zip(ref, bad)) if a != b]
    assert len(diffs) == 1


def test_near_duplicate_keys_exclude_real():
    r = TaskRng(7)
    keys = near_duplicate_keys(r, 1848, 5)
    assert len(keys) == len(set(keys)) == 5
    assert 1848 not in keys


def test_decoy_state_fields_modes():
    r = TaskRng(11)
    ref = "L9S3-2D8A"
    assert decoy_state_fields(ref, r, "a", "valid") == {
        "run_ref": ref, "artifact_state": "active"}
    wrong = decoy_state_fields(ref, r, "b", "wrong_ref")
    assert wrong["run_ref"] != ref and wrong["artifact_state"] == "active"
    inactive = decoy_state_fields(ref, r, "c", "inactive")
    assert inactive == {"run_ref": ref, "artifact_state": "inactive"}
    with pytest.raises(ValueError):
        decoy_state_fields(ref, r, "d", "bogus")


def test_injection_and_stale_text_contain_bait_only():
    r = TaskRng(13)
    real = mint_token(r, "L9S3-2D8A")
    fake = fake_token(r, "x", real)
    text = injection_text(r, "x", fake)
    assert fake in text and real not in text
    note = stale_note(r, "y", "2014-06-02")
    assert "2014-06-02" in note
