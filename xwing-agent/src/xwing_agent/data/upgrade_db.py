"""Upgrade card database with abilities derived from FlyCasual."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _load_database() -> dict:
    """Load the upgrade database from JSON file."""
    db_path = Path(__file__).parent / "upgrades.json"
    if db_path.exists():
        return json.loads(db_path.read_text())
    return {}


def get_upgrade_info(name: str) -> dict | None:
    """Get upgrade info by exact name.

    Returns dict with keys: types, charges, ability, summary, weapon (if applicable)
    """
    return _load_database().get(name)


def get_upgrade_summary(name: str) -> str:
    """Get short summary for an upgrade.

    Returns summary if available, otherwise ability text, otherwise empty string.
    """
    info = get_upgrade_info(name)
    if info:
        return info.get("summary", info.get("ability", ""))
    return ""


def get_all_upgrades() -> dict:
    """Get the entire upgrade database."""
    return _load_database()
