# -*- coding: utf-8 -*-
"""
profile.py — Local machine-only user profile + multi-profile (Switch) support.
Never uploaded anywhere.
"""
import os, json

PROFILE_EMOJIS = [
    # Animals
    "🦊","🐺","🐉","🦁","🐯","🐻","🐼","🦝","🦋","🌙",
    "🐧","🦆","🐸","🐢","🦎","🐍","🦂","🦀","🦞","🐬",
    "🐘","🦒","🦓","🦏","🦛","🐊","🦈","🐋","🦭","🦦",
    "🐿️","🦔","🦃","🦚","🦜","🦩","🕊️","🦅","🦇","🦑",
    "🐙","🦐","🦋","🐝","🐞","🦗","🦟","🐛","🐌","🕷️",
    # Nature & cosmos
    "⚡","🔥","❄️","🌊","🌪️","💎","🌑","🌟","☄️","🌈",
    "🌋","🏔️","🌺","🌸","🍄","🌿","🍀","🌵","🌴","🎋",
    # Objects & tech
    "🗡️","🛡️","⚔️","🔮","🎭","🤖","👾","💀","🔐","🏴",
    "🎲","🃏","♟️","🎮","🕹️","💻","🖥️","📡","🛸","🧬",
    "🔬","🧪","⚗️","🧲","🔭","🛰️","🚀","⚙️","🔩","💡",
    # Faces & symbols
    "😈","👻","💀","🤡","🎃","🧙","🧛","🧟","🧜","🧝",
    "🌞","🌝","🌛","🌜","⭐","🌠","🎯","🏆","💫","✨",
]

def _data_dir():
    from core.vault import DATA_DIR
    return DATA_DIR

def _profiles_path() -> str:
    return os.path.join(_data_dir(), "profiles.json")

def _current_id_path() -> str:
    return os.path.join(_data_dir(), "current_profile.txt")

# ── Current active profile ID ───────────────────────────────────────────────

def get_current_profile_id() -> str:
    try:
        with open(_current_id_path(), "r") as f:
            return f.read().strip() or "default"
    except Exception:
        return "default"

def set_current_profile_id(pid: str):
    os.makedirs(_data_dir(), exist_ok=True)
    with open(_current_id_path(), "w") as f:
        f.write(pid)

# ── Profile list CRUD ───────────────────────────────────────────────────────

def load_profiles() -> list:
    """Return list of all profile dicts: {id, username, avatar}"""
    try:
        with open(_profiles_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    return [{"id": "default", "username": "FluxUser", "avatar": "🦊"}]

def _save_profiles(profiles: list):
    os.makedirs(_data_dir(), exist_ok=True)
    with open(_profiles_path(), "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def load_profile(pid: str = None) -> dict:
    pid = pid or get_current_profile_id()
    for p in load_profiles():
        if p.get("id") == pid:
            return p
    return {"id": "default", "username": "FluxUser", "avatar": "🦊"}

def save_profile(username: str, avatar: str, pid: str = None):
    pid = pid or get_current_profile_id()
    profiles = load_profiles()
    for p in profiles:
        if p.get("id") == pid:
            p["username"] = username.strip() or "FluxUser"
            p["avatar"] = avatar
            _save_profiles(profiles)
            return
    profiles.append({"id": pid, "username": username.strip() or "FluxUser", "avatar": avatar})
    _save_profiles(profiles)

def create_profile(username: str, avatar: str) -> str:
    import secrets as _sec
    pid = "profile_" + _sec.token_hex(6)
    profiles = load_profiles()
    profiles.append({"id": pid, "username": username.strip() or "FluxUser", "avatar": avatar})
    _save_profiles(profiles)
    return pid

def delete_profile(pid: str):
    if pid == "default":
        return
    profiles = [p for p in load_profiles() if p.get("id") != pid]
    if not profiles:
        profiles = [{"id": "default", "username": "FluxUser", "avatar": "🦊"}]
    _save_profiles(profiles)
    # Clean up vault file for this profile
    vault_path = _profile_vault_path(pid)
    if os.path.exists(vault_path):
        os.remove(vault_path)

def _profile_vault_path(pid: str) -> str:
    if pid == "default":
        from core.vault import VAULT_FILE
        return VAULT_FILE
    return os.path.join(_data_dir(), f"vault_{pid}.json")
