"""
Give every card an English name for its energy types.

Each source prints a card's type in its own language — `Feuer`, `Feu`, `Fuego`
— and even the English-language sources disagree, Japanese writing `Electric`
and `Steel` where English writes `Lightning` and `Metal`. Searching or grouping
by type across languages needs one vocabulary.

The translation is not written by hand. Cards already link to their other
printings, so a German card joined to its English printing says what `Feuer`
means, and the corpus votes on every name at once. A name the links cannot
place is left alone rather than guessed at.

`types` keeps whatever the card itself prints; `types_en` is added beside it.

    uv run code/canonicalTypes.py            # derive the table and report
    uv run code/canonicalTypes.py --apply    # write types_en into the cards

September 17, 2026 by Weihang
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

import paths
from loguru import logger
from tqdm import tqdm

#: Sources that already print English type names. Their vocabulary is the one
#: every other language is translated into, so they are never rewritten.
CANONICAL = ("en", "tc", "sc", "pocket")


def card_files(langs):
    """Every stored card, one at a time.

    The corpus runs to six figures, so nothing here keeps a card after reading
    it: the vote needs three small fields, and the writing pass reads each file
    again when it is that card's turn.
    """
    for lang in langs:
        root = paths.data_dir(lang)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                yield lang, path, json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                logger.warning(f"Could not read {path}")


def collect_votes(langs):
    """What each language calls a type, and which cards link it to English.

    Only cards carrying a single type vote, because two printings of one card
    list their types in whatever order their sources chose, and a vote has to be
    unambiguous. Printings and fingerprints are both counted: together they
    reach the older sets that printings alone leave unlinked.
    """
    linked = {"print_key": defaultdict(list), "card_key": defaultdict(list)}
    vocabulary = defaultdict(set)
    seen = 0
    for lang, _, card in card_files(langs):
        seen += 1
        types = card.get("types") or []
        for kind in types:
            vocabulary[lang].add(str(kind))
        if len(types) != 1:
            continue
        for key_name, groups in linked.items():
            key = card.get(key_name)
            if key:
                groups[key].append((lang, str(types[0])))
    return seen, linked, vocabulary


def derive_table(linked):
    """Read the translation out of the linked printings."""
    votes = defaultdict(Counter)
    for groups in linked.values():
        for members in groups.values():
            english = {kind for lang, kind in members if lang in CANONICAL}
            if len(english) != 1:
                continue
            target = english.pop()
            for lang, kind in members:
                if lang not in CANONICAL:
                    votes[(lang, kind)][target] += 1

    table, confidence = {}, {}
    for (lang, kind), counter in votes.items():
        best, count = counter.most_common(1)[0]
        table[(lang, kind)] = best
        confidence[(lang, kind)] = (count, count / sum(counter.values()))
    return table, confidence


def report(vocabulary, table, confidence):
    """Say what the table covers, and what it cannot place."""
    for lang in sorted(vocabulary):
        if lang in CANONICAL:
            continue
        known = vocabulary[lang]
        placed = {kind for (found, kind) in table if found == lang}
        missing = sorted(known - placed)
        weakest = min(
            (confidence[(lang, kind)][1] for kind in placed if (lang, kind) in confidence),
            default=0,
        )
        logger.info(
            f"{lang}: {len(placed)} of {len(known)} type names placed, weakest agreement {weakest:.0%}"
        )
        for kind in sorted(placed):
            count, share = confidence[(lang, kind)]
            logger.info(f"    {kind} -> {table[(lang, kind)]}  ({count} linked cards, {share:.0%} agree)")
        if missing:
            logger.warning(f"    left alone, nothing links them: {', '.join(missing)}")


def english_types(lang, types, table):
    """The English names for one card's types, or None if any is unplaced."""
    named = []
    for kind in types:
        if lang in CANONICAL:
            named.append(str(kind))
            continue
        english = table.get((lang, str(kind)))
        if english is None:
            return None
        named.append(english)
    return named


def apply_table(langs, table, apply):
    """Write `types_en` beside the printed types."""
    written = unplaced = 0
    for lang, path, card in tqdm(card_files(langs), desc="Naming types", disable=None):
        types = card.get("types") or []
        if not types:
            continue
        named = english_types(lang, types, table)
        if named is None:
            unplaced += 1
            continue
        if card.get("types_en") == named:
            continue
        written += 1
        if apply:
            card["types_en"] = named
            path.write_text(json.dumps(card, indent=4, ensure_ascii=False), encoding="utf-8")
    return written, unplaced


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("langs", nargs="*", default=paths.LANGS, help=f"one or more of: {', '.join(paths.LANGS)}")
    parser.add_argument("--apply", action="store_true", help="write types_en into the card files")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    seen, linked, vocabulary = collect_votes(args.langs)
    logger.info(f"read {seen} cards")
    table, confidence = derive_table(linked)
    report(vocabulary, table, confidence)

    written, unplaced = apply_table(args.langs, table, args.apply)
    logger.info("")
    if args.apply:
        logger.info(f"named the types of {written} cards; {unplaced} carry a type the links cannot place")
    else:
        logger.info(f"{written} cards would gain types_en; {unplaced} carry a type the links cannot place")
        logger.info("Dry run. Re-run with --apply to write them.")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
