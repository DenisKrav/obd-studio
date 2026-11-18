"""Історія діагностики: результати сканувань зберігаються у obd_studio_history.json."""

import datetime
import json
from pathlib import Path

from .config import base_dir

HISTORY_FILE = "obd_studio_history.json"
MAX_ENTRIES = 300


def history_path():
    return base_dir() / HISTORY_FILE


def load_history(path=None):
    path = Path(path) if path else history_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []


def add_entry(entry, path=None, now=None):
    """Додає запис {vehicle, vin, protocol, stored, pending, permanent, mil} з датою."""
    path = Path(path) if path else history_path()
    entries = load_history(path)
    entry = dict(entry)
    entry["date"] = (now or datetime.datetime.now()).isoformat(timespec="seconds")
    entries.append(entry)
    entries = entries[-MAX_ENTRIES:]
    path.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    return entries
