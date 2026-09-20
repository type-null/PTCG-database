"""
Build the search index the card viewer reads.

The viewer needs enough per card to search and filter, but not the whole card:
the full file is fetched from `data_*/` only when a card is opened. That keeps
the index small enough to load in a browser while every stored field stays one
click away.

    uv run code/buildIndex.py

September 15, 2026 by Weihang
"""

import json
import sys

import paths
from cardkeys import one_card_per_language
from loguru import logger
from tqdm import tqdm

OUTPUT = paths.ROOT / "docs" / "index"

LANGS = paths.LANGS

#: What the card list and the filters need, in a fixed order per record.
FIELDS = [
    "name",
    "set_name",
    "number",
    "url",
    "card_type",
    "rarity",
    "hp",
    "types",
    "types_en",
    "tags",
    "stage",
    "regulation",
    "img",
    "path",
    "print_key",
    "card_key",
]


def write_index(path, payload):
    """Write an index the viewer reads straight from disk."""
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def type_words(card):
    """A card's types, as printed and in English, neither repeated.

    A search for `Fire` should reach `Feuer`, `Fuego` and `Feu`, and a search
    for `Feuer` should still reach the card the reader is looking at.
    """
    words = []
    for kind in (card.get("types") or []) + (card.get("types_en") or []):
        text = str(kind)
        if text not in words:
            words.append(text)
    return words


def text_of(card):
    """Every searchable line of a card, joined into one string."""
    parts = [card.get("name", ""), card.get("effect", "") or ""]
    for ability in card.get("abilities", []):
        parts += [ability.get("name", ""), ability.get("effect", "") or ""]
    for attack in card.get("attacks", []):
        parts += [attack.get("name", ""), attack.get("effect", "") or ""]
    parts += type_words(card)
    parts.append(card.get("rule_box", "") or "")
    parts.append(card.get("flavor_text", "") or "")
    return " ".join(part for part in parts if part)


def build(lang, print_groups, card_groups):
    """Write one language's index, and note which cards it links to."""
    root = paths.data_dir(lang)
    if not root.exists():
        return None
    records, complete, sets = [], [], {}
    # A language does not store the same fields everywhere — only Japanese has
    # `jp_id`, only some cards a rule box — so the hosted index takes the union
    # of what this language actually stores, and every card fills the columns
    # it has.
    stored_fields = set()
    files = sorted(root.rglob("*.json"))
    for path in tqdm(files, desc=f"Indexing {lang}", leave=False, disable=None):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.warning(f"Could not read {path}")
            continue
        card["path"] = str(path.relative_to(paths.ROOT))
        record = [card.get(field) for field in FIELDS]
        record.append(text_of(card))
        records.append(record)
        # The whole card, as the hosted page will show it. The repository path
        # means nothing there; the file name does, so a picture in the archive
        # beside the repository can still be named.
        whole = dict(card)
        whole["file"] = path.stem
        whole["text"] = record[-1]
        stored_fields.update(whole)
        complete.append(whole)

        # One entry per card, small enough to hold every link in one file.
        entry = [lang, card.get("name"), card.get("set_name"), str(card.get("number") or ""), card.get("rarity")]
        if card.get("print_key"):
            print_groups.setdefault(card["print_key"], []).append(entry)
        if card.get("card_key"):
            card_groups.setdefault(card["card_key"], []).append(entry)
        set_name = card.get("set_name") or "no_set"
        sets[set_name] = sets.get(set_name, 0) + 1

    OUTPUT.mkdir(parents=True, exist_ok=True)
    # The local viewer reads this one: every field a card stores, plus the path
    # it is stored at — which is how the page finds the card's picture in the
    # archive beside the repository.
    local_fields = sorted(stored_fields)
    (OUTPUT / f"{lang}.json").write_text(
        json.dumps(
            {
                "fields": local_fields,
                "cards": [[whole.get(field) for field in local_fields] for whole in complete],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    size = (OUTPUT / f"{lang}.json").stat().st_size
    logger.info(f"{lang}: {len(records)} cards, {len(sets)} sets, {size / 1e6:.1f} MB")
    return {"cards": len(records), "sets": sorted(sets), "bytes": size}


def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    summary, print_groups, card_groups = {}, {}, {}
    for lang in LANGS:
        result = build(lang, print_groups, card_groups)
        if result:
            summary[lang] = result

    # A set and number can hold several cards — reprints and rarity variants —
    # which describe themselves identically here. Show each once.
    def distinct(entries):
        seen, unique = set(), []
        for entry in entries:
            token = tuple(str(field) for field in entry)
            if token not in seen:
                seen.add(token)
                unique.append(entry)
        return unique

    links = {"prints": {}, "cards": {}}
    ambiguous = {"prints": 0, "cards": 0}
    #: A printing names one card per language. A fingerprint may hold a spelling
    #: variant of one card, but not a family of cards built alike.
    limits = {"prints": 1, "cards": 2}
    for name, groups in (("prints", print_groups), ("cards", card_groups)):
        for key, entries in groups.items():
            unique = distinct(entries)
            if len(unique) < 2:
                continue
            if not one_card_per_language(unique, limits[name]):
                ambiguous[name] += 1
                continue
            links[name][key] = unique
    logger.info(
        f"{ambiguous['prints']} printings are numbered ambiguously and "
        f"{ambiguous['cards']} fingerprints are shared by look-alike cards; neither links"
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_index(OUTPUT / "links.json", links)
    size = (OUTPUT / "links.json").stat().st_size
    logger.info(
        f"links: {len(links['prints'])} printings and {len(links['cards'])} cards "
        f"have more than one version ({size / 1e6:.1f} MB)"
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    total = sum(entry["cards"] for entry in summary.values())
    logger.info(f"Indexed {total} cards across {len(summary)} languages into {OUTPUT}")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
