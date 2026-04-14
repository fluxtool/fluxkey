# core/license_codes.py
# ── FluxKey PLUS activation code system ───────────────────────────────────────
#
#  Code format:  FLUX-XXXX-XXXX-XXXX-XXXX  (4 groups of 4)
#
#  Internals:
#    5 bytes nonce  +  5 bytes HMAC digest  =  10 bytes payload
#    base32(10 bytes) = exactly 16 chars  ->  4 groups of 4  ok
#
#  Change _SK to your own random bytes BEFORE distributing:
#    python -c "import os; print(list(os.urandom(32)))"
#
import hmac
import hashlib
import base64
import json
import os
import secrets

from core.vault import VAULT_FILE

# Secret key - CHANGE THIS before distributing
_SK = bytes([
    0x4b, 0x8f, 0x2a, 0x91, 0xe3, 0x17, 0x5c, 0xd4,
    0xa0, 0x6e, 0xbb, 0x38, 0x72, 0xf9, 0x04, 0x1d,
    0x95, 0xc2, 0x57, 0x3e, 0x80, 0x4f, 0xaa, 0x16,
    0xd7, 0x69, 0x2b, 0xe5, 0x0c, 0x43, 0x7a, 0xf1,
])

_NONCE_BYTES = 5
_SIG_BYTES   = 5

def _used_codes_path() -> str:
    return os.path.join(os.path.dirname(VAULT_FILE), "fluxkey_used_codes.json")

def _load_used() -> set:
    try:
        with open(_used_codes_path()) as f:
            return set(json.load(f))
    except Exception:
        return set()

def _save_used(used: set):
    try:
        with open(_used_codes_path(), "w") as f:
            json.dump(sorted(used), f, indent=2)
    except Exception:
        pass

def _sign(nonce: bytes) -> bytes:
    return hmac.new(_SK, nonce, hashlib.sha256).digest()[:_SIG_BYTES]

def _encode_code(nonce: bytes, sig: bytes) -> str:
    payload = nonce + sig
    b32 = base64.b32encode(payload).decode()
    chunks = [b32[i:i+4] for i in range(0, 16, 4)]
    return "FLUX-" + "-".join(chunks)

def _decode_code(code: str):
    code = code.strip().upper().replace(" ", "")
    if not code.startswith("FLUX-"):
        raise ValueError("Code must start with FLUX-")
    raw = code[5:].replace("-", "")
    if len(raw) != 16:
        raise ValueError(f"Wrong code length (got {len(raw)}, need 16)")
    try:
        payload = base64.b32decode(raw)
    except Exception:
        raise ValueError("Invalid characters in code")
    if len(payload) != _NONCE_BYTES + _SIG_BYTES:
        raise ValueError("Corrupt code payload")
    return payload[:_NONCE_BYTES], payload[_NONCE_BYTES:]

def generate_code() -> str:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    return _encode_code(nonce, _sign(nonce))

class CodeResult:
    OK           = "ok"
    INVALID      = "invalid"
    ALREADY_USED = "already_used"

def validate_and_activate(code: str) -> tuple:
    try:
        nonce, sig = _decode_code(code)
    except ValueError as e:
        return CodeResult.INVALID, str(e)

    if not hmac.compare_digest(_sign(nonce), sig):
        return CodeResult.INVALID, "Invalid code - please check and try again."

    used  = _load_used()
    canon = code.strip().upper().replace(" ", "")
    if canon in used:
        return CodeResult.ALREADY_USED, "This code has already been used."

    used.add(canon)
    _save_used(used)

    from core.license import set_plus
    set_plus(True)

    return CodeResult.OK, "FluxKey PLUS activated! Enjoy."