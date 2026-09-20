"""
Bring the whole database up to date in one run.

Every other script does one job; this one runs them in the order their results
depend on each other, so a routine update is a single command:

    uv run code/update.py                  # cards, keys, types, index, pictures
    uv run code/update.py --no-pictures    # skip the long download
    uv run code/update.py jp en            # only these languages
    uv run code/update.py --limit 20       # a short trial run
    uv run code/update.py --list           # show the steps and stop

The order matters. New cards arrive first; the identity keys are derived from
what a card stores, so they come next; the English type names are read out of
the links those keys make; the index is built from the finished cards; the
pictures are fetched from urls the cards carry; and the numbers the README
quotes are counted from the index once it is rebuilt.

Nothing here is destructive: every step skips what it already holds, so running
this twice in a row downloads nothing the second time. The one thing it cannot
do is republish the Artifact — that needs Claude — so it ends by saying so.

September 17, 2026 by Weihang
"""

import argparse
import collections
import json
import re
import subprocess
import sys
import time
from datetime import datetime

import paths
from loguru import logger

#: The languages kept up to date by default: the ones already stored.
LANGUAGES = ["jp", "en", "tc", "pocket", "ko", "fr", "de", "es", "it", "pt", "sc"]

#: Where the README's counts are written, so they cannot quietly go stale.
MARK_START = "<!-- numbers: written by code/update.py -->"
MARK_END = "<!-- end numbers -->"

#: And where the badges naming each language's newest set are written.
BADGE_START = "<!-- badges: written by code/update.py -->"
BADGE_END = "<!-- end badges -->"

#: How each source lets its sets be put in order of release. Only the TCGdex
#: languages and pkmncards publish a date; Japan and Korea number their cards
#: upwards, Taiwan numbers its pages, and TCG Pocket numbers its sets.
RECENCY = {
    "jp": "jp_id", "ko": "ko_id", "tc": "url", "pocket": "code", "en": "date",
    "de": "date", "fr": "date", "es": "date", "it": "date", "pt": "date", "sc": "date",
}

#: A promo set is numbered late without being the newest release, so it is never
#: what a badge should name.
PROMO = re.compile(r"(promo|^P-|[-_]P$|^SVP$|^MEP$|^BWP$|^XYP$|^SMP$|^DPP$|^HSP)", re.I)

#: Each language's own colour, and the name a reader would recognise.
SHIELD = {
    "jp": ("JP", "caaf2a"), "en": ("EN", "22498e"), "tc": ("TC", "e82927"),
    "ko": ("KO", "3d7dca"), "pocket": ("Pocket", "3ecaf2"), "de": ("DE", "111111"),
    "fr": ("FR", "2b5cc4"), "es": ("ES", "c60b1e"), "it": ("IT", "008c45"),
    "pt": ("PT", "006600"), "sc": ("SC", "de2910"),
}


def released(raw):
    """One release date, however that source happens to write it."""
    for shape in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(str(raw), shape)
        except ValueError:
            continue
    return None


def newest_set(lang):
    """The newest set this language holds, as (code, full name).

    Ranked by whatever that source gives to order releases by, with promo sets
    passed over: a promo is numbered late without being the newest release.
    """
    path = paths.ROOT / "docs" / "index" / f"{lang}.json"
    if not path.exists():
        return None
    index = json.loads(path.read_text(encoding="utf-8"))
    at = {name: spot for spot, name in enumerate(index["fields"])}
    how = RECENCY.get(lang, "date")

    ranked, titles, codes = collections.defaultdict(lambda: None), {}, {}
    for row in index["cards"]:
        name = str(row[at["set_name"]] or "")
        if not name:
            continue
        # Japan, Taiwan, Korea and pkmncards all keep the code a reader knows in
        # `set_name` — SCR, M6a. Only TCG Pocket puts a title there ("Deluxe
        # Pack: ex") and keeps its code, B4a, in `set_code`.
        code = str(row[at["set_code"]] or "") if "set_code" in at else ""
        looks_like_a_title = len(name) > 8 or " " in name
        codes.setdefault(name, code if looks_like_a_title and code else name)
        titles.setdefault(name, str(row[at.get("set_full_name", at["set_name"])] or name))

        if how == "date":
            mark = released(row[at["date"]]) if "date" in at else None
        elif how in ("jp_id", "ko_id"):
            raw = row[at[how]] if how in at else None
            mark = int(re.sub(r"\D", "", str(raw))) if raw else None
        elif how == "url":
            found = re.search(r"/(\d{3,})/?$", str(row[at["url"]] or ""))
            mark = int(found.group(1)) if found else None
        else:
            shape = re.match(r"([A-Z]+)(\d*)([a-z]*)$", codes[name])
            mark = (shape.group(1), int(shape.group(2) or 0), shape.group(3)) if shape else None
        if mark is not None and (ranked[name] is None or mark > ranked[name]):
            ranked[name] = mark

    order = sorted(((mark, name) for name, mark in ranked.items() if mark is not None), reverse=True)
    chosen = next((name for _, name in order if not PROMO.search(codes[name])), None)
    return (codes[chosen], titles[chosen]) if chosen else None


def badges():
    """A shield per language, naming the newest set stored for it."""
    lines = [BADGE_START, ""]
    for lang, (label, colour) in SHIELD.items():
        found = newest_set(lang)
        if not found:
            continue
        code, title = found
        # A shield is a url. A title that is not plain ASCII — 擴充包「30th
        # CELEBRATION」 — percent-encodes into something unreadable, and an
        # apostrophe or a stray dot reads no better, so those badges carry the
        # set's code alone. A literal dash has to be doubled to survive.
        plain = title.isascii() and all(ch.isalnum() or ch in " -" for ch in title)
        message = f"{code} {title}" if plain and title != code else code
        message = re.sub(r"\s+", "_", message.replace("-", "--"))
        lines.append(f"![{label} version](https://img.shields.io/badge/{label}-{message}-{colour})")
    lines += ["", BADGE_END]
    return "\n".join(lines)


def plan(languages, delay, limit, pictures):
    """Each step as a label and the command that runs it."""
    code = paths.ROOT / "code"
    here = [sys.executable]

    cards = [*here, str(code / "updateDatabase.py"), *languages]
    if delay:
        cards += ["--delay", str(delay)]
    if limit:
        cards += ["--limit", str(limit)]

    steps = [
        ("new cards", cards),
        ("repairs", [*here, str(code / "repairDatabase.py"), "--apply", "--langs", *languages]),
    ]
    # Japan and Korea state a Pokédex number for most of their cards but not all,
    # and a card's own name says which Pokémon it is. This fills only what those
    # sources leave blank, and runs before the keys, which are built from it.
    # English is left out on purpose: pkmncards publishes no number at all, and
    # the fingerprint already reads the species from the name where none is
    # stored, so filling it there would add a field the source never published.
    dex_langs = [name for name in languages if name in ("jp", "ko")]
    if dex_langs:
        steps.append(("pokedex numbers", [*here, str(code / "fillPokedex.py"), "--apply", *dex_langs]))
    steps += [
        ("identity keys", [*here, str(code / "linkCards.py"), "--apply", *languages]),
        ("english type names", [*here, str(code / "canonicalTypes.py"), "--apply", *languages]),
        ("search index", [*here, str(code / "buildIndex.py")]),
    ]
    if pictures:
        steps += [
            ("card pictures", [*here, str(code / "downloadImages.py"), "--apply", *languages]),
            ("picture checksums", [*here, str(code / "downloadImages.py"), "--verify", *languages]),
        ]
    steps.append(("tests", [*here, str(code / "test_scrapers.py")]))
    return steps


def run(label, command):
    """Run one step, echoing its output as it goes."""
    logger.info(f"===== {label} =====")
    started = time.time()
    finished = subprocess.run(command, cwd=paths.ROOT)
    took = time.time() - started
    if finished.returncode == 0:
        logger.info(f"----- {label}: done in {took:.0f}s")
    else:
        logger.error(f"----- {label}: exit code {finished.returncode} after {took:.0f}s")
    return finished.returncode == 0


def counted():
    """What the README should say, counted from what was just built."""
    index = paths.ROOT / "docs" / "index"
    summary = json.loads((index / "summary.json").read_text(encoding="utf-8"))
    rows = [(lang, entry["cards"], len(entry["sets"])) for lang, entry in summary.items()]
    cards = sum(count for _, count, _ in rows)

    links = json.loads((index / "links.json").read_text(encoding="utf-8"))
    archive = paths.ROOT.parent / "PTCG-card-images" / "manifest.json"
    pictures = json.loads(archive.read_text(encoding="utf-8")) if archive.exists() else {}

    lines = [
        MARK_START,
        "",
        f"**{cards:,} cards** across {len(rows)} languages, as of the last update.",
        "",
        "| language | cards | sets |",
        "| --- | --- | --- |",
        *[f"| `{lang}` | {count:,} | {sets} |" for lang, count, sets in sorted(rows)],
        "",
        f"- **{len(links['prints']):,} printings** and **{len(links['cards']):,} cards** "
        "are stored in more than one version",
        f"- **{len(pictures):,} pictures** archived beside the repository, "
        f"{sum(entry['bytes'] for entry in pictures.values()) / 1e9:.0f} GB",
        "",
        MARK_END,
    ]
    return "\n".join(lines)


def replace_block(text, start, end, written, what):
    """Swap one marked block for freshly written content, prose untouched."""
    if start not in text or end not in text:
        logger.warning(f"README has no {what} block; add {start} and {end} where it belongs")
        return text
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    logger.info(f"README {what} rewritten")
    return head + written + tail


def write_numbers():
    """Replace the README's counted and badge blocks, leaving the prose alone."""
    readme = paths.ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = replace_block(text, MARK_START, MARK_END, counted(), "numbers")
    text = replace_block(text, BADGE_START, BADGE_END, badges(), "badges")
    readme.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("languages", nargs="*", default=[], help=f"one or more of: {', '.join(LANGUAGES)}")
    parser.add_argument("--no-pictures", action="store_true", help="skip downloading and checksumming pictures")
    parser.add_argument("--delay", type=float, help="seconds between requests, to go easier on the sites")
    parser.add_argument("--limit", type=int, help="stop each source after this many cards or sets")
    parser.add_argument("--skip", nargs="*", default=[], help="step labels to leave out")
    parser.add_argument("--list", action="store_true", help="show the steps and stop")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | {message}")
    logger.add(paths.log_file("update.log"), level="INFO", encoding="utf-8")

    languages = args.languages or LANGUAGES
    unknown = [name for name in languages if name not in LANGUAGES]
    if unknown:
        parser.error(f"unknown language(s): {', '.join(unknown)}")

    steps = [step for step in plan(languages, args.delay, args.limit, not args.no_pictures)
             if step[0] not in args.skip]
    if args.list:
        for label, command in steps:
            print(f"  {label:20} {' '.join(command[1:])}")
        return 0

    started = time.time()
    done, failed = [], []
    for label, command in steps:
        (done if run(label, command) else failed).append(label)

    if not failed:
        write_numbers()

    logger.info("===== summary =====")
    logger.info(f"  {len(done)} steps done in {(time.time() - started) / 60:.0f} min: {', '.join(done)}")
    if failed:
        logger.error(f"  {len(failed)} failed: {', '.join(failed)}")
        logger.error("  the README numbers were left alone; fix the step and run again")
        return 1

    logger.info("  the viewer is ready: python3 -m http.server, then open /docs/")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    raise SystemExit(main())
