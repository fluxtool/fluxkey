# core/license.py
import os
import json

FREE_VAULT_LIMIT: int = 2
PLUS_VAULT_LIMIT: int = 9999

def _license_path() -> str:
    try:
        from core.vault import VAULT_FILE
        return os.path.join(os.path.dirname(VAULT_FILE), "fluxkey_license.json")
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "fluxkey_license.json")

# Mutate this dict in-place so all references stay valid
_cache: dict = {}

def _load() -> dict:
    if not _cache:
        try:
            with open(_license_path(), "r") as f:
                _cache.update(json.load(f))
        except Exception:
            _cache["plus"] = False
    return _cache

def _save():
    try:
        path = _license_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(_cache, f, indent=2)
    except Exception:
        pass

def is_plus() -> bool:
    return bool(_load().get("plus", False))

def set_plus(enabled: bool) -> None:
    _load()                          # ensure cache is populated
    _cache["plus"] = bool(enabled)   # mutate in-place — all refs see the change
    _save()

def vault_limit() -> int:
    return PLUS_VAULT_LIMIT if is_plus() else FREE_VAULT_LIMIT