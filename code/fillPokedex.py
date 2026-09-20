"""
Give a card the Pokédex number its own name already says.

Every fingerprint that links a card to its printings in other languages starts
with the Pokédex number, so a card without one links to nothing. Several sources
leave it out: Japan publishes it for most cards but not all, Korea for fewer, and
pkmncards for none at all — while all three print the species in the card's name.

The number is therefore read from the name, using the same species tables the
keys already use. It is only ever written where the source published none: a
number a source states is never overwritten, however odd it looks.

The rule was checked against the 14,456 Japanese cards that do carry a published
number: it agrees with 14,454 of them. The two it disagrees with are cards whose
stored number is wrong at the source (a ダストダス filed as 659, Bunnelby's
number), so the rule corrects them rather than breaking them — but they are left
alone all the same.

    uv run code/fillPokedex.py           # report what it would fill
    uv run code/fillPokedex.py --apply   # write the numbers in
    uv run code/fillPokedex.py jp ko     # only these languages

September 17, 2026 by Weihang
"""

import argparse
import json
import re
import sys
from collections import Counter

import cardkeys
import paths
from loguru import logger
from tqdm import tqdm

#: Values a source writes when it means "no number": a sentinel, not a Pokémon.
PLACEHOLDERS = {None, "", "0", "-1", 0, -1}


def published(raw):
    """The number a source actually states, or None where it states none."""
    if raw in PLACEHOLDERS:
        return None
    digits = re.sub(r"\D", "", str(raw))
    return int(digits) if digits else None


def fill(lang, apply):
    """Read the species out of each nameless card's name."""
    root = paths.data_dir(lang)
    if not root.exists():
        return Counter()

    tally = Counter()
    for path in tqdm(sorted(root.rglob("*.json")), desc=f"Reading {lang}", leave=False, disable=None):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.warning(f"Could not read {path}")
            continue

        # Only Pokémon have a Pokédex number; a Trainer or an Energy card has
        # none to find, and saying so would be a guess.
        if card.get("card_type") not in ("Pokémon", "Pokemon"):
            continue
        if published(card.get("pokedex_number")) is not None:
            tally["already published"] += 1
            continue

        found = cardkeys.dex_from_name(card.get("name"), lang)
        if not found:
            tally["name says nothing"] += 1
            continue

        tally["filled"] += 1
        if apply:
            card["pokedex_number"] = found
            for key in ("print_key", "card_key"):
                card.pop(key, None)
            card.update(cardkeys.keys_for(card))
            path.write_text(json.dumps(card, indent=4, ensure_ascii=False), encoding="utf-8")
    return tally


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("langs", nargs="*", default=paths.LANGS, help=f"one or more of: {', '.join(paths.LANGS)}")
    parser.add_argument("--apply", action="store_true", help="write the numbers into the cards")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    total = Counter()
    for lang in args.langs:
        tally = fill(lang, args.apply)
        total.update(tally)
        if tally:
            logger.info(
                f"{lang}: {tally['filled']} cards take the number their name says, "
                f"{tally['already published']} already carry one, "
                f"{tally['name says nothing']} cannot be placed"
            )

    logger.info("")
    if args.apply:
        logger.info(f"wrote a Pokédex number into {total['filled']} cards")
    else:
        logger.info(f"{total['filled']} cards would gain one. Re-run with --apply to write them.")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
