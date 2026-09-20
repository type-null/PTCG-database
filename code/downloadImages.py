"""
Archive the card images.

Every stored card already holds the url of its picture. This walks the card
files, downloads the pictures that are missing, and records a manifest so the
archive can be verified or rebuilt later.

The images are far too large for git (tens of gigabytes), so the archive sits
beside the repository rather than inside it — `../PTCG-card-images/` by default,
where git cannot see it at all. Its manifest lives with the pictures.

    uv run code/downloadImages.py                  # show what would be fetched
    uv run code/downloadImages.py --apply          # download them
    uv run code/downloadImages.py jp --apply       # one language at a time
    uv run code/downloadImages.py --apply --limit 50
    uv run code/downloadImages.py --apply --dir /Volumes/Archive/ptcg
    uv run code/downloadImages.py --verify        # checksum what is stored

September 15, 2026 by Weihang
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import paths
from CardScraper import CardScraper
from loguru import logger
from tqdm import tqdm

#: Beside the repository, never inside it: the archive runs to tens of
#: gigabytes, and git should never be asked to carry it. The manifest lives
#: with the pictures for the same reason.
DEFAULT_DIR = paths.ROOT.parent / "PTCG-card-images"
LANGS = paths.LANGS


def image_targets(lang, destination):
    """Every (url, destination) pair for one language."""
    root = paths.data_dir(lang)
    targets = {}
    for path in root.rglob("*.json"):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.warning(f"Could not read {path}")
            continue
        url = card.get("img")
        if not url:
            continue
        suffix = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if suffix not in ("jpg", "jpeg", "png", "webp", "gif"):
            suffix = "jpg"
        relative = path.relative_to(root).with_suffix(f".{suffix}")
        targets[destination / lang / relative] = url
    return targets


def load_manifest(manifest):
    if manifest.exists():
        try:
            return json.loads(manifest.read_text(encoding="utf-8"))
        except ValueError:
            logger.warning("Manifest is unreadable; starting a new one")
    return {}


def download(scraper, url, destination):
    """Fetch one image; returns its size and checksum, or None."""
    for attempt in range(1, scraper.retries + 1):
        scraper._wait_turn()
        try:
            response = scraper.session.get(url, timeout=scraper.timeout)
        except Exception as error:
            logger.warning(f"{url} failed ({error.__class__.__name__}), attempt {attempt}")
            scraper._back_off(attempt)
            continue
        if response.status_code == 200:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            return len(response.content), hashlib.sha256(response.content).hexdigest()
        if response.status_code in (403, 429) or response.status_code >= 500:
            logger.warning(f"{url} returned {response.status_code}, attempt {attempt}")
            scraper._back_off(attempt)
            continue
        logger.warning(f"{url} returned {response.status_code}; skipping")
        return None
    return None


def write_manifest(manifest_path, manifest):
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8"
    )


def verify(destination, manifest_path, manifest, langs):
    """Check every stored picture, and record any the manifest does not hold.

    The manifest is written as a run goes, but a run interrupted early can
    still leave pictures on disk that it never recorded. Their urls are read
    back out of the card files, so a rebuilt record is as complete as one
    written during the download.
    """
    urls = {}
    for lang in langs:
        if paths.data_dir(lang).exists():
            urls.update(image_targets(lang, destination))

    files = [path for path in destination.rglob("*") if path.is_file() and path.name != "manifest.json"]
    added = mismatched = empty = 0
    for path in tqdm(files, desc="Verifying", disable=None):
        key = str(path.relative_to(destination))
        content = path.read_bytes()
        if not content:
            empty += 1
            logger.warning(f"{key} is empty")
            continue
        digest = hashlib.sha256(content).hexdigest()
        entry = manifest.get(key)
        if entry is None:
            manifest[key] = {"url": urls.get(path), "bytes": len(content), "sha256": digest}
            added += 1
        elif entry.get("sha256") != digest:
            mismatched += 1
            logger.warning(f"{key} does not match the manifest")

    gone = [key for key in manifest if not (destination / key).exists()]
    for key in gone:
        manifest.pop(key)

    # A picture no card points at is left over from a card that has since moved
    # to another set folder. It is reported rather than deleted: the file is
    # still a good picture, and the next download fetches it under its new name.
    orphans = [path for path in files if path not in urls]

    write_manifest(manifest_path, manifest)
    logger.info(
        f"{len(files)} pictures stored: {added} added to the manifest, "
        f"{mismatched} did not match, {empty} empty, {len(gone)} recorded but gone"
    )
    logger.info(f"the manifest now holds {len(manifest)} pictures")
    if orphans:
        logger.info(f"{len(orphans)} pictures no card points at any more, such as:")
        for path in orphans[:5]:
            logger.info(f"    {path.relative_to(destination)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("langs", nargs="*", default=LANGS, help=f"one or more of: {', '.join(LANGS)}")
    parser.add_argument("--apply", action="store_true", help="actually download")
    parser.add_argument("--limit", type=int, help="stop after this many images")
    parser.add_argument("--delay", type=float, default=0.2, help="seconds between requests")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help=f"where to keep them (default {DEFAULT_DIR})")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="checksum the stored pictures and rebuild any part of the manifest that is missing",
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    logger.add(paths.log_file("download_images.log"), level="INFO", encoding="utf-8")

    destination = Path(args.dir).expanduser()
    manifest_path = destination / "manifest.json"
    logger.info(f"archive: {destination}")
    manifest = load_manifest(manifest_path)

    if args.verify:
        verify(destination, manifest_path, manifest, args.langs)
        return

    scraper = CardScraper(delay=args.delay)

    for lang in args.langs:
        if not paths.data_dir(lang).exists():
            continue
        targets = image_targets(lang, destination)
        pending = {dest: url for dest, url in targets.items() if not dest.exists()}
        logger.info(f"{lang}: {len(targets)} images, {len(pending)} missing")
        if not args.apply:
            continue

        items = list(pending.items())
        if args.limit:
            items = items[: args.limit]
        for count, (target, url) in enumerate(tqdm(items, desc=f"Images {lang}", disable=None), start=1):
            result = download(scraper, url, target)
            if result:
                size, digest = result
                manifest[str(target.relative_to(destination))] = {
                    "url": url,
                    "bytes": size,
                    "sha256": digest,
                }
            # A language runs for hours. Keep the record on disk as it goes, so
            # an interrupted run still describes every picture it fetched.
            if count % 200 == 0:
                write_manifest(manifest_path, manifest)
        write_manifest(manifest_path, manifest)
        logger.info(f"{lang}: archive now holds {len(manifest)} images")

    if not args.apply:
        logger.info("Dry run. Re-run with --apply to download.")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
