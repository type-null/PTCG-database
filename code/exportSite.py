"""Export the existing Card Atlas as an independent, offline static website.

    python3 code/exportSite.py --output site --language en --limit 48

No dependencies, server, network or generated search index are required.
The export keeps the viewer and complete records; only the dataset is selected.
"""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote, urlsplit

from cardkeys import one_card_per_language

ROOT = Path(__file__).resolve().parent.parent
REPORT = "export-report.json"
SCHEMA = "ptcg-database-export-v1"
PREFERRED_NAMES = ("Pikachu", "Charizard", "Bulbasaur", "Squirtle", "Eevee", "Mew", "Mewtwo", "Ultra Ball", "Professor's Research")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def script_json(value):
    # JSON inside an HTML script is still parsed by the HTML parser first.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def read_sources(directory):
    # Many small files are expensive to open serially on a cold filesystem.
    # Bounded batches keep memory small; map preserves sorted source order.
    files = sorted(directory.rglob("*.json"))
    with ThreadPoolExecutor(max_workers=16) as workers:
        for offset in range(0, len(files), 256):
            batch = files[offset:offset + 256]
            yield from zip(batch, workers.map(Path.read_bytes, batch))


def read_cards(root, languages):
    records, fingerprints = {}, {}
    for language in languages:
        directory = root / f"data_{language}"
        if not directory.is_dir():
            raise ValueError(f"No stored cards for language {language}: {directory}")
        records[language] = []
        fingerprint = hashlib.sha256()
        for source, raw in read_sources(directory):
            card = json.loads(raw)
            if not isinstance(card, dict) or not card.get("name"):
                raise ValueError(f"Invalid card record: {source}")
            stored = source.relative_to(root).as_posix()
            fingerprint.update(stored.encode() + b"\0" + raw + b"\0")
            card.update(path=stored, file=source.stem)
            words = [card.get("name"), card.get("effect"), card.get("rule_box"), card.get("flavor_text")]
            for item in card.get("abilities", []) + card.get("attacks", []):
                words.extend((item.get("name"), item.get("effect")))
            words.extend(card.get("types") or [])
            words.extend(card.get("types_en") or [])
            card["text"] = " ".join(str(word) for word in words if word)
            records[language].append(card)
        if not records[language]:
            raise ValueError(f"No stored cards for language {language}")
        fingerprints[language] = fingerprint.hexdigest()
    return records, fingerprints


def release_rank(card):
    value = str(card.get("date") or "")
    for pattern in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, pattern).toordinal()
        except ValueError:
            pass
    return 0


def choose_cards(cards, limit, sets=()):
    """A deterministic varied sample: familiar names, print pairs, types, sets."""
    candidates = [card for card in cards if not sets or card.get("set_name") in sets]
    if not candidates:
        raise ValueError(f"No cards match the requested sets: {', '.join(sets)}")
    if limit == 0 or len(candidates) <= limit:
        return candidates
    recent = sorted(candidates, key=lambda card: (release_rank(card), card["path"]), reverse=True)
    chosen, seen = [], set()

    def add(card):
        if card["path"] not in seen and len(chosen) < limit:
            chosen.append(card)
            seen.add(card["path"])

    for name in PREFERRED_NAMES:
        card = next((card for card in recent if card["name"] == name), None)
        if card:
            add(card)
    # A pair makes the viewer's other-printings control useful in the sample.
    for card in list(chosen):
        if card.get("card_key"):
            partner = next((other for other in recent if other["path"] != card["path"] and other.get("card_key") == card["card_key"] and other["name"] == card["name"]), None)
            if partner:
                add(partner)
    for field in ("card_type", "types_en"):
        covered = set()
        for card in chosen:
            values = card.get(field) or []
            covered.update(values if isinstance(values, list) else [values])
        for card in recent:
            values = card.get(field) or []
            values = values if isinstance(values, list) else [values]
            if any(value not in covered for value in values):
                add(card)
                covered.update(values)
    # Fill by walking sets, rather than allowing one recent set to dominate.
    groups = defaultdict(list)
    for card in recent:
        groups[str(card.get("set_name") or "")].append(card)
    while len(chosen) < limit:
        for group in groups.values():
            if group:
                add(group.pop(0))
    return chosen


def make_links(all_records, selected):
    groups = {"prints": defaultdict(list), "cards": defaultdict(list)}
    selected_paths = {card["path"] for cards in selected.values() for card in cards}
    for language, cards in all_records.items():
        for card in cards:
            entry = [language, card["name"], card.get("set_name"), str(card.get("number") or ""), card.get("rarity")]
            for group, key in (("prints", "print_key"), ("cards", "card_key")):
                if card.get(key):
                    groups[group][card[key]].append((card["path"], entry))
    links = {"prints": {}, "cards": {}}
    for group, keyed in groups.items():
        for key, rows in keyed.items():
            # Same ambiguity rule as cardkeys.one_card_per_language, applied to
            # all source records before selecting the entries the export holds.
            if not one_card_per_language([entry for _, entry in rows], 1 if group == "prints" else 2):
                continue
            entries = []
            for path, entry in rows:
                if path in selected_paths and entry not in entries:
                    entries.append(entry)
            if len(entries) > 1:
                links[group][key] = entries
    return links


def image_file(card, root, archive):
    url = card.get("img")
    if not isinstance(url, str) or not url:
        return None
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        suffix = ".jpg"
    relative = Path(card["path"].replace("data_", "", 1)).with_suffix(suffix)
    candidates = [archive / relative] if archive else [root / "images" / relative, root.parent / "PTCG-card-images" / relative]
    return next((path for path in candidates if path.is_file() and path.stat().st_size), None)


def validate_destination(root, output):
    if output.is_symlink():
        raise ValueError("Output must not be a symlink")
    output = output.resolve()
    if output == root or root.is_relative_to(output):
        raise ValueError("Output must not contain the repository")
    if output.is_relative_to(root) and output != root / "site" and not output.is_relative_to(root / "dist"):
        raise ValueError("Exports inside this repository must use site/ or a folder under dist/")
    if output.exists() and not output.is_dir():
        raise ValueError("Output is not a directory")
    if output.exists() and any(output.iterdir()):
        marker = output / REPORT
        try:
            report = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError("Refusing to replace an unmanaged output directory") from error
        if report.get("schema") != SCHEMA or not isinstance(report.get("files"), dict):
            raise ValueError("Output has no valid export ownership report")
        actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
        if any(path.is_symlink() for path in output.rglob("*")) or actual != set(report["files"]) | {REPORT}:
            raise ValueError("Output contains unmanaged files or symlinks; choose a new directory")
        for relative, expected in report["files"].items():
            if digest(output / relative) != expected:
                raise ValueError(f"Output was edited: {relative}; choose a new directory")
    return output


def render_viewer(root, bundle):
    viewer = (root / "docs/index.html").read_text(encoding="utf-8")
    marker = "<!-- portable-data -->"
    if viewer.count(marker) != 1:
        raise ValueError("Viewer lacks the supported portable-data hook")
    return viewer.replace(marker, f'<script id="portable-data" type="application/json">{script_json(bundle)}</script>')


def publish_directory(stage, output):
    """Replace a validated generated directory, retaining rollback on failure."""
    backup = None
    if output.exists():
        backup = Path(tempfile.mkdtemp(prefix=".ptcg-previous-", dir=output.parent))
        backup.rmdir()
        output.rename(backup)
    try:
        stage.rename(output)
    except OSError:
        if backup:
            backup.rename(output)
        raise
    if backup:
        shutil.rmtree(backup)


def export_site(root, output, languages=("en",), limit=48, sets=(), archive=None):
    root = root.resolve()
    if limit < 0:
        raise ValueError("Limit must be zero (all) or positive")
    if not languages or any(not language.isalpha() for language in languages):
        raise ValueError("Languages must be letter-only codes, such as en or jp")
    languages = tuple(dict.fromkeys(languages))
    output = validate_destination(root, output)
    all_records, fingerprints = read_cards(root, languages)
    selected = {language: choose_cards(cards, limit, sets) for language, cards in all_records.items()}
    files, summary, images = {}, {}, {}
    for language, cards in selected.items():
        fields = sorted({field for card in cards for field in card})
        files[f"index/{language}.json"] = {"fields": fields, "cards": [[card.get(field) for field in fields] for card in cards]}
        summary[language] = {"cards": len(cards), "source_cards": len(all_records[language]), "sets": sorted({str(card.get("set_name") or "") for card in cards})}
    files["index/summary.json"] = summary
    files["index/links.json"] = make_links(all_records, selected)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".ptcg-export-", dir=output.parent))
    try:
        for cards in selected.values():
            for card in cards:
                source = image_file(card, root, archive)
                if source:
                    relative = "images/" + card["path"].replace("data_", "", 1).rsplit(".", 1)[0] + source.suffix.lower()
                    target = stage / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    images[card["path"]] = quote(relative, safe="/")
        generated = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        count = sum(len(cards) for cards in selected.values())
        bundle = {"files": files, "images": images, "generated_at": generated}
        viewer = render_viewer(root, bundle)
        (stage / "index.html").write_text(viewer, encoding="utf-8")
        report = {
            "schema": SCHEMA, "source_repository": "https://github.com/type-null/PTCG-database",
            "generated_at": generated, "selection": {"limit_per_language": limit, "sets": list(sets), "method": "varied: familiar names, printing pairs, types, then sets"},
            "cards": count, "languages": summary, "local_images": len(images), "missing_images": count - len(images),
            "source_data_sha256": fingerprints,
            "viewer_sha256": digest(root / "docs/index.html"),
            "files": {path.relative_to(stage).as_posix(): digest(path) for path in sorted(stage.rglob("*")) if path.is_file()},
        }
        (stage / REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        publish_directory(stage, output)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    parser.add_argument("--language", nargs="+", default=["en"], help="stored language codes; default en")
    parser.add_argument("--limit", type=int, default=48, help="cards per language; 0 includes all")
    parser.add_argument("--set", action="append", default=[], dest="sets", help="exact stored set_name; repeat for several sets")
    parser.add_argument("--images", type=Path, help="image archive root holding en/<set>/<card>.jpg etc.")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        report = export_site(ROOT, output, args.language, args.limit, args.sets, args.images)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Export failed: {error}\n")
    print(f"Exported {report['cards']} cards, {report['local_images']} local pictures, {report['missing_images']} text faces to {output.resolve() / 'index.html'}")


if __name__ == "__main__":
    main()
