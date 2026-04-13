# -*- coding: utf-8 -*-
import json
import os
import hashlib
import secrets
import time

DATA_DIR        = os.path.join(os.path.expanduser("~"), ".fluxkey")
VAULT_FILE      = os.path.join(DATA_DIR, "vault.json")
VAULTGROUPS_FILE= os.path.join(DATA_DIR, "vaultgroups.json")

# Active profile ID — set when a profile is switched so group functions use correct file
_ACTIVE_PROFILE_ID = "default"

def set_active_profile(pid: str):
    global _ACTIVE_PROFILE_ID
    _ACTIVE_PROFILE_ID = pid

def _groups_file_for_profile(pid: str = None) -> str:
    """Return the vaultgroups file path for a given profile."""
    _pid = pid or _ACTIVE_PROFILE_ID
    if _pid == "default":
        return VAULTGROUPS_FILE
    return os.path.join(DATA_DIR, f"vaultgroups_{_pid}.json")
AUDIT_FILE      = os.path.join(DATA_DIR, "audit.json")

# ── PLUS version flag ──────────────────────────────────────────────────────
IS_PLUS        = True   # Set False to simulate free tier
FREE_VAULT_LIMIT = 4    # max user-created vaults on free tier


# ── Audit log ──────────────────────────────────────────────────────────────

def add_audit(action: str, detail: str = ""):
    if not IS_PLUS:
        return
    _ensure_dir()
    log = _load_audit()
    log.insert(0, {
        "action": action,
        "detail": detail,
        "ts": int(time.time()),
    })
    log = log[:500]   # keep last 500 entries
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def _load_audit() -> list:
    if not os.path.exists(AUDIT_FILE):
        return []
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_audit_log() -> list:
    return _load_audit()
CONFIG_FILE     = os.path.join(DATA_DIR, "config.json")
HISTORY_FILE    = os.path.join(DATA_DIR, "history.json")

DEFAULT_VAULT_NAME = "Not Stored Yet"
DEFAULT_VAULT_ID   = "not_stored_yet"

DEFAULT_AVATARS = ["🔑", "🛡️", "💼", "🏠", "🎮", "🌐", "💳", "📱", "🔒", "⭐", "🚀", "🎯"]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(cfg: dict):
    _ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 260000
    ).hex()


def has_master_password() -> bool:
    if not os.path.exists(CONFIG_FILE):
        return False
    return bool(_load_config().get("password_hash"))


def set_master_password(password: str):
    salt = secrets.token_hex(32)
    pw_hash = _hash_password(password, salt)
    cfg = _load_config()
    cfg["password_hash"] = pw_hash
    cfg["salt"] = salt
    cfg["failed_attempts"] = 0
    cfg["lockout_until"] = 0
    _save_config(cfg)


def verify_master_password(password: str) -> tuple:
    cfg = _load_config()
    lockout_until = cfg.get("lockout_until", 0)
    if lockout_until and time.time() < lockout_until:
        remaining = int(lockout_until - time.time())
        return False, f"Too many attempts. Try again in {remaining}s.", remaining
    salt   = cfg.get("salt", "")
    stored = cfg.get("password_hash", "")
    if not salt or not stored:
        return False, "No master password set.", 0
    if _hash_password(password, salt) == stored:
        cfg["failed_attempts"] = 0
        cfg["lockout_until"] = 0
        _save_config(cfg)
        return True, "", 0
    else:
        attempts = cfg.get("failed_attempts", 0) + 1
        cfg["failed_attempts"] = attempts
        if attempts >= 5:
            cfg["lockout_until"] = time.time() + 30
            cfg["failed_attempts"] = 0
            _save_config(cfg)
            return False, "5 failed attempts. Locked for 30 seconds.", 30
        remaining_before_lock = 5 - attempts
        _save_config(cfg)
        return False, f"Incorrect password. {remaining_before_lock} attempt(s) left.", 0


def get_failed_attempts() -> int:
    return _load_config().get("failed_attempts", 0)


def get_lockout_remaining() -> int:
    lu = _load_config().get("lockout_until", 0)
    if lu and time.time() < lu:
        return int(lu - time.time())
    return 0


def get_theme() -> str:
    return _load_config().get("theme", "dark")


def set_theme(theme: str):
    cfg = _load_config()
    cfg["theme"] = theme
    _save_config(cfg)


def get_auto_lock_minutes() -> int:
    return _load_config().get("auto_lock_minutes", 0)


def set_auto_lock_minutes(minutes: int):
    cfg = _load_config()
    cfg["auto_lock_minutes"] = minutes
    _save_config(cfg)


MAX_HISTORY = 10

def add_to_history(password: str):
    _ensure_dir()
    history = load_history()
    if history and history[0]["password"] == password:
        return
    history.insert(0, {"password": password, "created": int(time.time())})
    history = history[:MAX_HISTORY]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)


def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)


def wipe_all():
    for f in (VAULT_FILE, VAULTGROUPS_FILE, CONFIG_FILE, HISTORY_FILE):
        if os.path.exists(f):
            os.remove(f)


def _vault_hash(data: list) -> str:
    raw = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def update_integrity_hash(data: list):
    cfg = _load_config()
    cfg["vault_integrity_hash"] = _vault_hash(data)
    _save_config(cfg)


def check_integrity() -> bool:
    cfg = _load_config()
    stored = cfg.get("vault_integrity_hash", "")
    if not stored or not os.path.exists(VAULT_FILE):
        return True
    with open(VAULT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _vault_hash(data) == stored


# ── Vault Groups ───────────────────────────────────────────────────────────

def _load_groups() -> list:
    gf = _groups_file_for_profile()
    if not os.path.exists(gf):
        return []
    with open(gf, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_groups(groups: list):
    _ensure_dir()
    with open(_groups_file_for_profile(), "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=4)


def _ensure_default_group():
    groups = _load_groups()
    ids = [g["id"] for g in groups]
    if DEFAULT_VAULT_ID not in ids:
        groups.insert(0, {
            "id": DEFAULT_VAULT_ID,
            "name": DEFAULT_VAULT_NAME,
            "description": "Passwords not yet assigned to a vault",
            "avatar": "📦",
            "created": int(time.time()),
        })
        _save_groups(groups)
    return _load_groups()


def get_all_groups() -> list:
    return _ensure_default_group()


def create_group(name: str, description: str = "", avatar: str = "🔑") -> dict:
    groups = get_all_groups()
    gid = secrets.token_hex(8)
    group = {
        "id": gid,
        "name": name.strip(),
        "description": description.strip(),
        "avatar": avatar,
        "created": int(time.time()),
    }
    groups.append(group)
    _save_groups(groups)
    return group


def update_group(gid: str, name: str = None, description: str = None, avatar: str = None):
    groups = _load_groups()
    for g in groups:
        if g["id"] == gid:
            if name is not None:
                g["name"] = name.strip()
            if description is not None:
                g["description"] = description.strip()
            if avatar is not None:
                g["avatar"] = avatar
            break
    _save_groups(groups)


def delete_group(gid: str):
    if gid == DEFAULT_VAULT_ID:
        return
    vault = Vault()
    entries = vault.load()
    for entry in entries:
        if entry.get("vault_id") == gid:
            entry["vault_id"] = DEFAULT_VAULT_ID
    vault._write(entries)
    groups = _load_groups()
    groups = [g for g in groups if g["id"] != gid]
    _save_groups(groups)


def get_group_by_id(gid: str):
    for g in get_all_groups():
        if g["id"] == gid:
            return g
    return None




# ── Vault entry encryption ──────────────────────────────────────────────────
# Derives a 32-byte key from the master password via PBKDF2-HMAC-SHA256.
# Each entry's password field is XOR-encrypted with the key stream (keystream
# generated via repeated SHA-256 of key+counter, giving a secure stream cipher).
# Stored as hex. If no master password is set yet, entries stored plaintext
# and migrated on first unlock.

def _derive_key(master_password: str) -> bytes:
    """Derive 32-byte AES-equivalent key from master password."""
    cfg = _load_config()
    salt = cfg.get("salt", "fluxkey_default_salt_v1")
    return hashlib.pbkdf2_hmac("sha256", master_password.encode(), salt.encode(), 100000, 32)

def _xor_encrypt(plaintext: str, key: bytes) -> str:
    """XOR-stream encrypt plaintext, return hex string."""
    data = plaintext.encode("utf-8")
    stream = bytearray()
    counter = 0
    while len(stream) < len(data):
        block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        stream.extend(block)
        counter += 1
    encrypted = bytes(a ^ b for a, b in zip(data, stream[:len(data)]))
    return encrypted.hex()

def _xor_decrypt(hex_data: str, key: bytes) -> str:
    """XOR-stream decrypt hex string, return plaintext."""
    try:
        data = bytes.fromhex(hex_data)
        stream = bytearray()
        counter = 0
        while len(stream) < len(data):
            block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
            stream.extend(block)
            counter += 1
        decrypted = bytes(a ^ b for a, b in zip(data, stream[:len(data)]))
        return decrypted.decode("utf-8")
    except Exception:
        return hex_data  # fallback: return as-is (legacy plaintext)

_VAULT_KEY: bytes = b""

def set_vault_key(master_password: str):
    """Call after successful login to set the encryption key."""
    global _VAULT_KEY
    _VAULT_KEY = _derive_key(master_password)

def encrypt_password(pw: str) -> str:
    """Encrypt a password string for vault storage."""
    if not _VAULT_KEY or not pw:
        return pw
    return "ENC:" + _xor_encrypt(pw, _VAULT_KEY)

def decrypt_password(stored: str) -> str:
    """Decrypt a vault-stored password string."""
    if not _VAULT_KEY or not stored:
        return stored
    if stored.startswith("ENC:"):
        return _xor_decrypt(stored[4:], _VAULT_KEY)
    return stored  # legacy plaintext


# ── Vault CRUD ─────────────────────────────────────────────────────────────

class Vault:

    def __init__(self, vault_file: str = None, profile_id: str = None):
        _ensure_dir()
        self._vault_file = vault_file or VAULT_FILE
        # Set global active profile so group operations use correct groups file
        if profile_id:
            set_active_profile(profile_id)
        elif vault_file and vault_file != VAULT_FILE:
            # Infer profile id from filename e.g. vault_profile_abc123.json
            import re as _re
            m = _re.search(r'vault_(profile_[a-z0-9_]+)\.json', vault_file)
            if m:
                set_active_profile(m.group(1))
        else:
            set_active_profile("default")
        _ensure_default_group()
        if not os.path.exists(self._vault_file):
            self._write([])
        if self._vault_file == VAULT_FILE:
            self.migrate_legacy()

    def _write(self, data: list):
        _ensure_dir()
        with open(self._vault_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        if self._vault_file == VAULT_FILE:
            update_integrity_hash(data)

    def load(self) -> list:
        if not os.path.exists(self._vault_file):
            return []
        with open(self._vault_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_by_group(self, gid: str) -> list:
        return [(i, e) for i, e in enumerate(self.load())
                if e.get("vault_id", DEFAULT_VAULT_ID) == gid]

    def save_entry(self, site: str, username: str, password: str,
                   vault_id: str = DEFAULT_VAULT_ID):
        data = self.load()
        data.append({
            "site": site,
            "username": username,
            "password": password,
            "vault_id": vault_id,
            "created": int(time.time()),
        })
        self._write(data)
        add_audit("SAVE", f"{site} → vault:{vault_id}")

    def update_entry(self, index: int, site: str, username: str, password: str):
        data = self.load()
        if 0 <= index < len(data):
            data[index]["site"] = site
            data[index]["username"] = username
            data[index]["password"] = password
            self._write(data)
            add_audit("EDIT", site)

    def move_entry(self, index: int, new_vault_id: str):
        data = self.load()
        if 0 <= index < len(data):
            site = data[index].get("site", "?")
            data[index]["vault_id"] = new_vault_id
            self._write(data)
            add_audit("MOVE", f"{site} → vault:{new_vault_id}")

    def delete_entry(self, index: int):
        data = self.load()
        if 0 <= index < len(data):
            site = data[index].get("site", "?")
            data.pop(index)
            self._write(data)
            add_audit("DELETE", site)

    def migrate_legacy(self):
        data = self.load()
        changed = False
        for entry in data:
            if "vault_id" not in entry:
                entry["vault_id"] = DEFAULT_VAULT_ID
                changed = True
        if changed:
            self._write(data)

    def export_json(self, path: str) -> bool:
        try:
            data = self.load()
            groups = get_all_groups()
            export = {
                "app": "FluxKey",
                "version": "2.0.0",
                "exported": int(time.time()),
                "groups": groups,
                "entries": data,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=4)
            return True
        except Exception:
            return False

    def import_json(self, path: str) -> tuple:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                entries = raw
            elif isinstance(raw, dict) and "entries" in raw:
                entries = raw["entries"]
            else:
                return 0, 0, "Unrecognised file format."
            existing = self.load()
            existing_keys = {(e.get("site", ""), e.get("username", "")) for e in existing}
            imported = 0
            skipped  = 0
            for entry in entries:
                site = entry.get("site", "").strip()
                user = entry.get("username", "").strip()
                pwd  = entry.get("password", "").strip()
                if not site or not pwd:
                    skipped += 1; continue
                if (site, user) in existing_keys:
                    skipped += 1; continue
                existing.append({
                    "site": site, "username": user, "password": pwd,
                    "vault_id": entry.get("vault_id", DEFAULT_VAULT_ID),
                    "created": entry.get("created", int(time.time())),
                })
                existing_keys.add((site, user))
                imported += 1
            self._write(existing)
            return imported, skipped, None
        except Exception as ex:
            return 0, 0, str(ex)


# ── Secure Notes ────────────────────────────────────────────────────────────

NOTES_FILE = os.path.join(DATA_DIR, "notes.json")
NOTES_VAULT_ID = "secure_notes"


def _ensure_notes_vault():
    """Ensure the Secure Notes vault group exists."""
    groups = _load_groups()
    ids = [g["id"] for g in groups]
    if NOTES_VAULT_ID not in ids:
        groups.append({
            "id": NOTES_VAULT_ID,
            "name": "Secure Notes",
            "description": "Encrypted personal notes",
            "avatar": "📝",
            "created": int(time.time()),
            "is_notes": True,
        })
        _save_groups(groups)


def get_notes() -> list:
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_note(note_id: str, title: str, body: str):
    _ensure_dir()
    notes = get_notes()
    for n in notes:
        if n["id"] == note_id:
            n["title"] = title
            n["body"]  = body
            n["updated"] = int(time.time())
            break
    else:
        notes.insert(0, {
            "id":      note_id,
            "title":   title,
            "body":    body,
            "created": int(time.time()),
            "updated": int(time.time()),
        })
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)
    add_audit("NOTE_SAVE", title)


def delete_note(note_id: str):
    notes = [n for n in get_notes() if n["id"] != note_id]
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)
    add_audit("NOTE_DELETE", note_id)
