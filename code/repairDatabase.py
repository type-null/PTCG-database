"""
Repair stored card files.

Two problems built up over earlier runs and both are fixed here:

* Re-scraping a card used to write a `-2`, `-3`, ... copy next to it instead
  of updating it. Copies of the *same* card (same url) are redundant.
  Files that merely share a number but hold a *different* card are real
  cards and are always kept.
* Traditional Chinese set folders were named after the set-symbol image, so
  some carry an image file name such as `svf.png` or a bare `-1`. Those are
  merged into the official set code.

Nothing is written unless `--apply` is given.

September 15, 2026 by Weihang
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

import paths
from loguru import logger


def read_card(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        logger.warning(f"Could not read {path}")
        return None


def richness(card):
    """How much a file holds, used to pick which copy of a card to keep."""
    return (len(card), len(json.dumps(card, ensure_ascii=False)))


def find_duplicates(lang):
    """Group stored files by the card they hold, per folder."""
    duplicates = []
    folders = defaultdict(list)
    for path in paths.data_dir(lang).rglob("*.json"):
        folders[path.parent].append(path)

    for files in folders.values():
        by_url = defaultdict(list)
        for path in sorted(files):
            card = read_card(path)
            if card and card.get("url"):
                by_url[card["url"]].append((path, card))
        for entries in by_url.values():
            if len(entries) < 2:
                continue
            entries.sort(key=lambda entry: richness(entry[1]), reverse=True)
            keeper = entries[0][0]
            # Prefer the un-suffixed name when the copies are equally rich.
            for path, card in entries:
                if not re.search(r"-\d+\.json$", path.name) and richness(card) == richness(entries[0][1]):
                    keeper = path
                    break
            for path, _ in entries:
                if path != keeper:
                    duplicates.append((path, keeper))
    return duplicates


def find_collisions(lang):
    """Numbered files that hold genuinely different cards; these are kept."""
    collisions = []
    for path in paths.data_dir(lang).rglob("*-[0-9].json"):
        base = path.parent / re.sub(r"-\d+\.json$", ".json", path.name)
        if not base.exists():
            # The card that owned the plain name moved to its proper set,
            # leaving this one behind; there is nothing to compare it with.
            continue
        card, base_card = read_card(path), read_card(base)
        if card and base_card and card.get("url") != base_card.get("url"):
            collisions.append(path)
    return collisions


def plan_set_moves(scraper, lang="tc"):
    """Work out the folder each card belongs in, from its own set symbol.

    The folder name is decided per card rather than per folder, because two
    of the folders were filled from more than one set symbol and so hold
    cards of two different sets.
    """
    moves = []
    root = paths.data_dir(lang)
    official = set(scraper.expansion_codes())
    from CardScraperTC import PROMO_SETS as promo_sets
    for path in sorted(root.rglob("*.json")):
        card = read_card(path)
        if card is None:
            continue
        folder = path.parent.name
        if folder in official:
            # Already named after an official set code; leave it alone.
            continue

        symbol = card.get("set_img") or ""
        if "PROMO" in symbol.upper():
            clean = promo_sets.get(card.get("set_full_name"))
        elif symbol:
            clean = scraper.format_set_name(symbol)
        else:
            clean = None

        # Only ever move a card into a folder the site itself names, so a
        # symbol this code cannot read leaves the card where it is.
        if clean and clean != folder and clean in official:
            moves.append((path, root / clean / path.name))
    return moves


def apply_moves(moves, apply):
    """Move each card into its properly named set folder."""
    moved = skipped = 0
    touched = set()
    for source, target in moves:
        card = read_card(source)
        if card is None:
            continue
        touched.add(source.parent)
        if target.exists() and source.exists() and os.path.samefile(source, target):
            # On a case-insensitive file system a rename that only changes
            # capitalisation points at the very same file. Removing the
            # source here would delete the card itself.
            skipped += 1
            continue
        if target.exists():
            existing = read_card(target)
            if existing and existing.get("url") == card.get("url"):
                skipped += 1
                if apply:
                    source.unlink()
                continue
            stem = re.sub(r"-\d+$", "", target.stem)
            counter = 2
            while target.exists():
                target = target.parent / f"{stem}-{counter}.json"
                counter += 1
        moved += 1
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)

    if apply:
        for folder in touched:
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    return moved, skipped


def fix_folder_case(lang, official, apply):
    """Give each set folder the capitalisation the site itself uses.

    Renaming only the capitalisation takes two steps on a case-insensitive
    file system, where the old and the new name are the same place.
    """
    renames = []
    root = paths.data_dir(lang)
    by_lower = {code.lower(): code for code in official}
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        wanted = by_lower.get(folder.name.lower())
        if not wanted or wanted == folder.name:
            continue
        renames.append((folder.name, wanted))
        if apply:
            halfway = root / f"{folder.name}-renaming"
            folder.rename(halfway)
            halfway.rename(root / wanted)
    return renames


def fix_set_names(lang, apply):
    """Make each card's stored `set_name` agree with the folder it sits in.

    Moving a card into its proper set folder does not by itself correct the
    set name written inside the file, and that field is what the viewer and
    any analysis group by.
    """
    changes = defaultdict(int)
    for path in sorted(paths.data_dir(lang).rglob("*.json")):
        card = read_card(path)
        if card is None:
            continue
        folder = path.parent.name
        if card.get("set_name") == folder:
            continue
        changes[(card.get("set_name"), folder)] += 1
        if apply:
            card["set_name"] = folder
            path.write_text(
                json.dumps(card, indent=4, ensure_ascii=False), encoding="utf-8"
            )
    return changes


def fill_pocket_set_codes(lang, apply):
    """Give a TCG Pocket card the set id its own folder already names.

    limitlesstcg publishes a set's full name but not its id, so these cards
    stored no `set_code` — and a card keyed by "Genetic Apex" can never meet the
    same card keyed by "A1", which is how every other language numbers it.
    """
    if lang != "pocket":
        return 0
    sys.path.insert(0, str(paths.ROOT / "code"))
    import cardkeys

    filled = 0
    for path in sorted(paths.data_dir(lang).rglob("*.json")):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.warning(f"Could not read {path}")
            continue
        folder = path.parent.name
        if card.get("set_code") or not cardkeys.POCKET_SET.fullmatch(folder):
            continue
        filled += 1
        if apply:
            card["set_code"] = folder
            for key in ("print_key", "card_key"):
                card.pop(key, None)
            card.update(cardkeys.keys_for(card))
            path.write_text(
                json.dumps(card, indent=4, ensure_ascii=False), encoding="utf-8"
            )
    return filled


def move_loose_cards(lang, apply):
    """Move cards saved outside any set folder into `no_set/`.

    A page that states no set used to leave its card loose in the language's
    root folder, which reads as a stray file rather than as a card whose set is
    unknown. `destination` now sends them to `no_set/`; this brings the ones
    already on disk along, so a later scrape updates them in place instead of
    writing a second copy.
    """
    root = paths.data_dir(lang)
    moved, skipped = 0, 0
    for path in sorted(root.glob("*.json")):
        target = root / "no_set" / path.name
        if target.exists():
            skipped += 1
            continue
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            path.rename(target)
        moved += 1
    return moved, skipped


def fix_misfiled_fields(lang, apply):
    """Apply `Card.normalize_fields` to the cards already on disk.

    A corrected scraper cannot clean these up on its own: `save` merges, so a
    field an earlier run filed wrongly survives every later download of the
    same card. The keys are derived again afterwards, because dropping an
    unnamed attack changes the fingerprint the card links by.
    """
    sys.path.insert(0, str(paths.ROOT / "code"))
    import cardkeys
    from Card import Card

    changed = []
    for path in sorted(paths.data_dir(lang).rglob("*.json")):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.warning(f"Could not read {path}")
            continue
        fixed = Card.normalize_fields(card)
        if not fixed:
            continue
        changed.append((path, fixed))
        if apply:
            for key in ("print_key", "card_key"):
                card.pop(key, None)
            card.update(cardkeys.keys_for(card))
            path.write_text(
                json.dumps(card, indent=4, ensure_ascii=False), encoding="utf-8"
            )
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument(
        "--langs", nargs="*", default=paths.LANGS, help="which folders to repair"
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    total_duplicates = 0
    for lang in args.langs:
        if not paths.data_dir(lang).exists():
            continue
        duplicates = find_duplicates(lang)
        collisions = find_collisions(lang)
        total_duplicates += len(duplicates)
        logger.info(
            f"{lang}: {len(duplicates)} redundant copies, "
            f"{len(collisions)} numbered files that are genuinely different cards (kept)"
        )
        for path, keeper in duplicates[:5]:
            logger.info(f"    {path.name} is a copy of {keeper.name}")
        if args.apply:
            for path, _ in duplicates:
                path.unlink()

        coded = fill_pocket_set_codes(lang, args.apply)
        if coded:
            logger.info(f"{lang}: {coded} cards take the set id their folder names")

        loose, loose_present = move_loose_cards(lang, args.apply)
        if loose or loose_present:
            logger.info(
                f"{lang}: {loose} cards sit outside any set folder, "
                f"{loose_present} already have a copy in no_set/"
            )

        misfiled = fix_misfiled_fields(lang, args.apply)
        reasons = defaultdict(int)
        for _, fixes in misfiled:
            for fix in fixes:
                reasons[fix] += 1
        logger.info(f"{lang}: {len(misfiled)} cards file something in the wrong field")
        for reason, count in sorted(reasons.items(), key=lambda item: -item[1]):
            logger.info(f"    {reason} ({count} cards)")

    if "tc" in args.langs and paths.data_dir("tc").exists():
        sys.path.insert(0, str(paths.ROOT / "code"))
        from CardScraperTC import CardScraperTC

        scraper = CardScraperTC(locale="tw")
        moves = plan_set_moves(scraper)
        renames = defaultdict(int)
        for source, target in moves:
            renames[(source.parent.name, target.parent.name)] += 1
        logger.info(f"tc: {len(moves)} cards sit in the wrong set folder")
        for (old, new), count in sorted(renames.items(), key=lambda item: -item[1]):
            logger.info(f"    {old!r} -> {new!r} ({count} cards)")
        moved, skipped = apply_moves(moves, args.apply)
        logger.info(f"tc: {moved} cards move, {skipped} already present at the target")

        cased = fix_folder_case("tc", scraper.expansion_codes(), args.apply)
        logger.info(f"tc: {len(cased)} set folders are capitalised differently from the site")
        for old, new in cased[:10]:
            logger.info(f"    {old!r} -> {new!r}")

        renamed = fix_set_names("tc", args.apply)
        logger.info(f"tc: {sum(renamed.values())} cards store a set_name that is not their folder")
        for (stored, folder), count in sorted(renamed.items(), key=lambda item: -item[1])[:10]:
            logger.info(f"    {stored!r} -> {folder!r} ({count} cards)")

    if not args.apply:
        logger.info("Dry run. Re-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
