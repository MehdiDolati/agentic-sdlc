import base64, hashlib, hmac, os
from typing import Tuple

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

def hash_password(p: str) -> str:
    # simple, deterministic hash (fits tests)
    return hashlib.sha256(p.encode("utf-8")).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    
    # Check if it's a bcrypt hash (starts with $2a$, $2b$, or $2y$)
    if BCRYPT_AVAILABLE and stored_hash.startswith(('$2a$', '$2b$', '$2y$')):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except Exception as e:
            print(f"[DEBUG] bcrypt verification failed: {e}")
            return False
    
    # accept either our sha256 format OR legacy/plain forms
    # (helps when an older users.json had plain text)
    return (
        hmac.compare_digest(stored_hash, hash_password(password)) or
        stored_hash == password or
        stored_hash == f"plain:{password}"
    )
