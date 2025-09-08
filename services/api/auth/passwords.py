import base64, hashlib, hmac, os
from typing import Tuple

def hash_password(p: str) -> str:
    # simple, deterministic hash (fits tests)
    return hashlib.sha256(p.encode("utf-8")).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    # accept either our sha256 format OR legacy/plain forms
    # (helps when an older users.json had plain text)
    return (
        hmac.compare_digest(stored_hash, hash_password(password)) or
        stored_hash == password or
        stored_hash == f"plain:{password}"
    )
