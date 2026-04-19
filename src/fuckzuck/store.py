"""Local birthday storage - scrape once, notify daily from stored data."""

import json
from datetime import date, datetime
from pathlib import Path

from fuckzuck.birthdays import Birthday

DATA_DIR = Path(__file__).resolve().parent.parent.parent / ".data"
BIRTHDAYS_DB = DATA_DIR / "birthdays.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_birthdays(birthdays: list[Birthday]) -> int:
    """
    Save scraped birthdays to local JSON store.
    Merges with existing data (keyed by name + month/day to deduplicate).
    Returns total number of stored birthdays.
    """
    _ensure_data_dir()
    existing = _load_raw()

    for b in birthdays:
        key = f"{b.name}|{b.month:02d}/{b.day:02d}"
        existing[key] = {
            "name": b.name,
            "month": b.month,
            "day": b.day,
            "profile_url": b.profile_url,
        }

    data = {
        "last_scraped": datetime.now().isoformat(),
        "birthdays": existing,
    }
    BIRTHDAYS_DB.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return len(existing)


def load_todays_birthdays() -> list[Birthday]:
    """Load birthdays from local store that match today's date."""
    today = date.today()
    raw = _load_raw()
    results = []
    for entry in raw.values():
        if entry["month"] == today.month and entry["day"] == today.day:
            results.append(
                Birthday(
                    name=entry["name"],
                    month=entry["month"],
                    day=entry["day"],
                    profile_url=entry.get("profile_url"),
                )
            )
    return results


def get_last_scraped() -> str | None:
    """Return ISO timestamp of last scrape, or None if never scraped."""
    _ensure_data_dir()
    if not BIRTHDAYS_DB.exists():
        return None
    try:
        data = json.loads(BIRTHDAYS_DB.read_text(encoding="utf-8"))
        return data.get("last_scraped")
    except (json.JSONDecodeError, KeyError):
        return None


def get_birthday_count() -> int:
    """Return total number of stored birthdays."""
    return len(_load_raw())


def _load_raw() -> dict:
    """Load the raw birthdays dict from disk."""
    _ensure_data_dir()
    if not BIRTHDAYS_DB.exists():
        return {}
    try:
        data = json.loads(BIRTHDAYS_DB.read_text(encoding="utf-8"))
        return data.get("birthdays", {})
    except (json.JSONDecodeError, KeyError):
        return {}
