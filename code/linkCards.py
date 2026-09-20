"""
Give every stored card its identity keys, and report what they link.

New cards get their keys when they are saved. This fills them in for the cards
that were downloaded before the keys existed, and prints what the links look
like so the result can be judged rather than trusted.

    uv run code/linkCards.py                 # report only
    uv run code/linkCards.py --apply         # write the keys into the cards
    uv run code/linkCards.py --apply jp ko   # only these languages

September 16, 2026 by Weihang
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

from loguru import logger

import cardkeys
import paths


def read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        logger.warning(f"Could not read {path}")
        return None


def add_keys(langs, apply):
    """Write both keys into every card that is missing them."""
    written = 0
    cards = defaultdict(list)  # print_key -> [(lang, name, set, number, rarity)]
    groups = defaultdict(list)  # card_key  -> same
    for lang in langs:
        root = paths.data_dir(lang)
        if not root.exists():
            continue
        changed = 0
        for path in sorted(root.rglob("*.json")):
            card = read(path)
            if card is None:
                continue
            keys = cardkeys.keys_for(card)
            if any(card.get(name) != value for name, value in keys.items()):
                card.update(keys)
                changed += 1
                if apply:
                    path.write_text(
                        json.dumps(card, indent=4, ensure_ascii=False), encoding="utf-8"
                    )
            entry = (lang, card.get("name"), card.get("set_name"), card.get("number"), card.get("rarity"))
            if keys.get("print_key"):
                cards[keys["print_key"]].append(entry)
            if keys.get("card_key"):
                groups[keys["card_key"]].append(entry)
        written += changed
        logger.info(f"{lang}: {changed} cards to key")
    return written, cards, groups


def report(cards, groups):
    """Say how much the keys actually link."""
    def languages(entries):
        return {entry[0] for entry in entries}

    shared_print = {k: v for k, v in cards.items() if len(languages(v)) > 1}
    shared_card = {k: v for k, v in groups.items() if len(languages(v)) > 1}
    variants = {k: v for k, v in groups.items() if len(v) > 1}

    # Count what the viewer will actually offer. A key can be real and still
    # name no single card — promos that reuse a number, or a family built alike —
    # and the index leaves those out, so the report must not claim them.
    from cardkeys import one_card_per_language

    vague_prints = {k for k, v in shared_print.items() if not one_card_per_language(v, 1)}
    vague_cards = {k for k, v in variants.items() if not one_card_per_language(v, 2)}
    shared_print = {k: v for k, v in shared_print.items() if k not in vague_prints}
    shared_card = {k: v for k, v in shared_card.items() if k not in vague_cards}
    variants = {k: v for k, v in variants.items() if k not in vague_cards}

    logger.info("")
    logger.info(
        f"of those crossing languages, set aside as naming no single card: "
        f"{len(vague_prints)} printings, {len(vague_cards)} fingerprints "
        f"(buildIndex withholds more: it judges groups inside one language too)"
    )
    logger.info(f"exact printings that exist in more than one language: {len(shared_print)}")
    logger.info(f"   languages per printing: {dict(Counter(len(languages(v)) for v in shared_print.values()))}")
    logger.info(f"fingerprinted cards found in more than one language: {len(shared_card)}")
    logger.info(f"cards with more than one printing (rarity or set variants): {len(variants)}")

    for title, sample in (("an exact printing", shared_print), ("a fingerprinted card", variants)):
        if not sample:
            continue
        key = max(sample, key=lambda k: len(sample[k]))
        logger.info("")
        logger.info(f"largest {title} — {key}")
        for lang, name, set_name, number, rarity in sorted(sample[key])[:10]:
            logger.info(f"    {lang:7} {str(name)[:22]:24} {str(set_name):8} {str(number):>6}  {rarity or ''}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("langs", nargs="*", default=paths.LANGS, help=f"one or more of: {', '.join(paths.LANGS)}")
    parser.add_argument("--apply", action="store_true", help="write the keys into the card files")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    written, cards, groups = add_keys(args.langs, args.apply)
    report(cards, groups)
    logger.info("")
    if args.apply:
        logger.info(f"wrote keys into {written} cards")
    else:
        logger.info(f"{written} cards would gain keys. Re-run with --apply to write them.")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
