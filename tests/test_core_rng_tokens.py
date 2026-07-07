from thb.core.rng import TaskRng
from thb.core.tokens import mint_token, token_hash, verify_token, looks_like_token


def test_same_seed_same_values():
    a, b = TaskRng(42), TaskRng(42)
    assert a.randint("x", 0, 10 ** 9) == b.randint("x", 0, 10 ** 9)
    assert a.code("c", 8) == b.code("c", 8)
    assert a.shuffle("s", range(20)) == b.shuffle("s", range(20))


def test_different_names_independent():
    r = TaskRng(42)
    assert r.code("a", 12) != r.code("b", 12)


def test_different_seeds_differ():
    assert TaskRng(1).code("x", 12) != TaskRng(2).code("x", 12)


def test_order_independence():
    r1 = TaskRng(7)
    v_first = r1.randint("alpha", 0, 10 ** 9)
    r2 = TaskRng(7)
    r2.randint("beta", 0, 10 ** 9)  # draw something else first
    assert v_first == r2.randint("alpha", 0, 10 ** 9)


def test_child_streams_stable_and_distinct():
    r = TaskRng(99)
    assert r.child("L1").code("x", 8) == TaskRng(99).child("L1").code("x", 8)
    assert r.child("L1").code("x", 8) != r.child("L2").code("x", 8)


def test_token_mint_and_verify():
    r = TaskRng(5)
    tok = mint_token(r, "L1S1-ABCD")
    assert looks_like_token(tok)
    assert tok == mint_token(TaskRng(5), "L1S1-ABCD")  # deterministic
    assert tok != mint_token(TaskRng(5), "L1S2-ABCD")  # run-id scoped
    h = token_hash(tok)
    assert verify_token(tok, h)
    assert verify_token("  %s \n" % tok, h)  # whitespace tolerated
    assert not verify_token(tok.lower(), h)
