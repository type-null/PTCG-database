"""
Check for updates for all games.

One entry point for every source:

    uv run code/updateDatabase.py                 # every source
    uv run code/updateDatabase.py jp en           # only these
    uv run code/updateDatabase.py --list          # what can be updated
    uv run code/updateDatabase.py jp --limit 20   # a short trial run
    uv run code/updateDatabase.py --delay 2       # go easier on the site

Each source downloads only the cards it does not already hold, so running
this twice in a row costs one listing pass and downloads nothing.

May 1, 2025 by Weihang
"""

import argparse
import sys
import time

import paths
from loguru import logger

#: name -> (module, class, keyword arguments, log file)
SOURCES = {
    "jp": ("CardScraperJP", "CardScraperJP", {}, "scrape_jp_log.log"),
    "en": ("CardScraperEN", "CardScraperEN", {}, "scrape_en_log.log"),
    "tc": ("CardScraperTC", "CardScraperTC", {"locale": "tw"}, "scrape_tc_log.log"),
    "pocket": ("CardScraperPocket", "CardScraperPocket", {}, "scrape_pocket_log.log"),
    "ko": ("CardScraperKO", "CardScraperKO", {}, "scrape_ko_log.log"),
    "hk": ("CardScraperTC", "CardScraperTC", {"locale": "hk"}, "scrape_hk_log.log"),
    "th": ("CardScraperTC", "CardScraperTC", {"locale": "th"}, "scrape_th_log.log"),
    "id": ("CardScraperTC", "CardScraperTC", {"locale": "id"}, "scrape_id_log.log"),
    "sg": ("CardScraperTC", "CardScraperTC", {"locale": "sg"}, "scrape_sg_log.log"),
    "my": ("CardScraperTC", "CardScraperTC", {"locale": "my"}, "scrape_my_log.log"),
    "ph": ("CardScraperTC", "CardScraperTC", {"locale": "ph"}, "scrape_ph_log.log"),
    # Languages with no official card database to read, served by TCGdex.
    "fr": ("CardScraperTCGdex", "CardScraperTCGdex", {"lang": "fr"}, "scrape_fr_log.log"),
    "de": ("CardScraperTCGdex", "CardScraperTCGdex", {"lang": "de"}, "scrape_de_log.log"),
    "es": ("CardScraperTCGdex", "CardScraperTCGdex", {"lang": "es"}, "scrape_es_log.log"),
    "it": ("CardScraperTCGdex", "CardScraperTCGdex", {"lang": "it"}, "scrape_it_log.log"),
    "pt": ("CardScraperTCGdex", "CardScraperTCGdex", {"lang": "pt"}, "scrape_pt_log.log"),
    "sc": ("CardScraperTCGdex", "CardScraperTCGdex", {"lang": "zh-cn"}, "scrape_sc_log.log"),
}

#: Updated by default; the rest are opt-in because they are new and large.
DEFAULT_SOURCES = ["jp", "en", "tc", "pocket"]


def build_scraper(name, delay):
    module_name, class_name, kwargs, _ = SOURCES[name]
    module = __import__(module_name)
    scraper = getattr(module, class_name)(**kwargs)
    if delay:
        scraper.delay = delay
    return scraper


def configure_logging(name, verbose):
    """Log to the console and to this source's own log file."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}",
    )
    logger.add(
        paths.log_file(SOURCES[name][3]),
        level="DEBUG" if verbose else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {module} | {message}",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="*", default=[], help=f"one or more of: {', '.join(SOURCES)}")
    parser.add_argument("--all", action="store_true", help="include the newer languages too")
    parser.add_argument("--list", action="store_true", help="show the sources and stop")
    parser.add_argument("--limit", type=int, help="stop after this many cards or sets")
    parser.add_argument("--delay", type=float, help="seconds between requests (default 1)")
    parser.add_argument("--verbose", action="store_true", help="log every field that is read")
    args = parser.parse_args()

    if args.list:
        for name, (_, _, kwargs, _) in SOURCES.items():
            default = "default" if name in DEFAULT_SOURCES else "opt-in"
            extra = f" ({kwargs})" if kwargs else ""
            print(f"  {name:8} {default}{extra}")
        return

    sources = args.sources or (list(SOURCES) if args.all else DEFAULT_SOURCES)
    unknown = [name for name in sources if name not in SOURCES]
    if unknown:
        parser.error(f"unknown source(s): {', '.join(unknown)}")

    results = {}
    for name in sources:
        configure_logging(name, args.verbose)
        started = time.time()
        try:
            scraper = build_scraper(name, args.delay)
            scraper.update(limit=args.limit)
            results[name] = f"done in {time.time() - started:.0f}s"
        except KeyboardInterrupt:
            results[name] = "interrupted"
            logger.warning(f"{name}: interrupted; progress so far is saved")
            break
        except Exception as error:
            results[name] = f"failed: {error.__class__.__name__}: {error}"
            logger.exception(f"{name}: update failed")

    configure_logging(sources[0], args.verbose)
    logger.info("===== Summary =====")
    for name, outcome in results.items():
        logger.info(f"  {name:8} {outcome}")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
    main()
