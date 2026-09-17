from app.ledger import canonical
import hashlib

def test_canonical_is_deterministic():
    a = canonical({"b": 2, "a": 1})
    b = canonical({"a": 1, "b": 2})
    assert a == b

def test_sha256_length():
    assert len(hashlib.sha256(b"evidence").hexdigest()) == 64
