"""
Repository paths.

Anchoring every path to the repository root lets the scrapers run from any
working directory instead of only from the repository root.

September 15, 2026 by Weihang
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LOGS = ROOT / "logs"
README = ROOT / "README.md"

DATA = {
    "jp": ROOT / "data_jp",
    "en": ROOT / "data_en",
    "tc": ROOT / "data_tc",
    "pocket": ROOT / "data_pocket",
    "ko": ROOT / "data_ko",
}

#: Every game and language the database can hold, in the order tools report
#: them. Kept here so adding a language reaches every tool at once.
LANGS = [
    "jp",
    "en",
    "tc",
    "pocket",
    "ko",
    # Pokémon Asia locales
    "hk",
    "th",
    "id",
    "sg",
    "my",
    "ph",
    # languages served by TCGdex
    "fr",
    "de",
    "es",
    "it",
    "pt",
    "sc",
]


def data_dir(lang):
    """Folder holding the card files of one game/language."""
    if lang in DATA:
        return DATA[lang]
    return ROOT / f"data_{lang}"


def log_file(name):
    """Path of a bookkeeping file, creating `logs/` on first use."""
    LOGS.mkdir(parents=True, exist_ok=True)
    return LOGS / name
