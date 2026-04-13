# -*- coding: utf-8 -*-
"""
FluxKey audit log — rich event tracking.
Stored as newline-delimited JSON in ~/.fluxkey/audit.jsonl
"""
import json, os, time, socket
from core.vault import DATA_DIR

AUDIT_FILE  = os.path.join(DATA_DIR, "audit.jsonl")
MAX_ENTRIES = 1000


def log(action: str, detail: str = "", extra: dict = None):
    os.makedirs(DATA_DIR, exist_ok=True)
    entry = {
        "ts":     int(time.time()),
        "action": action,
        "detail": detail,
    }
    if extra:
        entry.update(extra)
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    _trim()


def load() -> list:
    if not os.path.exists(AUDIT_FILE):
        return []
    lines = []
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except Exception:
                    pass
    return list(reversed(lines))


def _trim():
    entries = load()
    if len(entries) > MAX_ENTRIES:
        entries = entries[:MAX_ENTRIES]
        with open(AUDIT_FILE, "w", encoding="utf-8") as f:
            for e in reversed(entries):
                f.write(json.dumps(e) + "\n")


def clear():
    if os.path.exists(AUDIT_FILE):
        os.remove(AUDIT_FILE)
