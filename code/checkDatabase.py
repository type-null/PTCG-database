"""
Report on the health of the stored cards.

Reads every card file and says what is missing or surprising, so a scraper
that quietly stops reading a field shows up as a number rather than as a
card someone notices months later.

    uv run code/checkDatabase.py            # every language
    uv run code/checkDatabase.py jp en      # only these
    uv run code/checkDatabase.py --sets     # also list per-set counts

September 15, 2026 by Weihang
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

from loguru import logger

import paths

LANGS = paths.LANGS

#: Every card must carry these, whatever its language or kind.
REQUIRED = ["url", "name", "img", "card_type", "set_name", "number"]

#: A Pokémon must also carry these.
POKEMON_REQUIRED = ["hp", "types", "stage"]

POKEMON_TYPES = {"Pokémon", "Pokemon"}


def load(lang):
    for path in sorted(paths.data_dir(lang).rglob("*.json")):
        try:
            yield path, json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.warning(f"Could not read {path}")


def check(lang, show_sets):
    root = paths.data_dir(lang)
    if not root.exists():
        return

    total = 0
    missing = Counter()
    rarities = Counter()
    card_types = Counter()
    sets = Counter()
    numbers = defaultdict(list)
    no_rule_tag = []

    for path, card in load(lang):
        total += 1
        for field in REQUIRED:
            if card.get(field) in (None, "", []):
                missing[field] += 1
        if card.get("card_type") in POKEMON_TYPES:
            for field in POKEMON_REQUIRED:
                if card.get(field) in (None, "", []):
                    missing[field] += 1
        rarities[card.get("rarity")] += 1
        card_types[card.get("card_type")] += 1
        set_name = card.get("set_name") or "no_set"
        sets[set_name] += 1
        if card.get("number") not in (None, ""):
            # Cards that state no number are filed by their own id instead,
            # so they are not competing for the same name.
            numbers[(set_name, str(card["number"]))].append(path.name)
        if card.get("rule_box") and not card.get("tags"):
            no_rule_tag.append(path.name)

    logger.info(f"=== {lang}: {total} cards, {len(sets)} sets ===")
    if missing:
        for field, count in missing.most_common():
            logger.info(f"    missing {field}: {count} ({100 * count / total:.1f}%)")
    else:
        logger.info("    every card carries the required fields")

    clashes = {key: names for key, names in numbers.items() if len(names) > 1}
    logger.info(f"    numbers used by more than one file: {len(clashes)}")
    for (set_name, number), names in list(clashes.items())[:5]:
        logger.info(f"        {set_name} {number}: {', '.join(sorted(names))}")

    if no_rule_tag:
        logger.info(f"    rule box but no tag: {len(no_rule_tag)} (e.g. {no_rule_tag[:3]})")

    logger.info(f"    card types: {dict(card_types.most_common(8))}")
    logger.info(f"    rarities: {len(rarities)} distinct, top {dict(rarities.most_common(5))}")

    if show_sets:
        for set_name, count in sorted(sets.items()):
            logger.info(f"        {set_name}: {count}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("langs", nargs="*", default=LANGS, help=f"one or more of: {', '.join(LANGS)}")
    parser.add_argument("--sets", action="store_true", help="also list the cards per set")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    for lang in args.langs:
        check(lang, args.sets)


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
