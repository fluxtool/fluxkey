# -*- coding: utf-8 -*-
"""
FluxKey secure notes store — PLUS feature.
Stored in ~/.fluxkey/notes.json as a list of note objects.
"""
import json, os, time, secrets
from core.vault import DATA_DIR

NOTES_FILE = os.path.join(DATA_DIR, "notes.json")


def _load() -> list:
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(notes: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)


def get_notes() -> list:
    return sorted(_load(), key=lambda n: n.get("updated", 0), reverse=True)


def save_note(note_id: str, title: str, body: str):
    notes = _load()
    now = int(time.time())
    for note in notes:
        if note["id"] == note_id:
            note["title"]   = title
            note["body"]    = body
            note["updated"] = now
            _save(notes)
            return
    # New note
    notes.append({
        "id":      note_id,
        "title":   title,
        "body":    body,
        "created": now,
        "updated": now,
    })
    _save(notes)


def delete_note(note_id: str):
    notes = [n for n in _load() if n["id"] != note_id]
    _save(notes)
