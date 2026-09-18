"""
    Scrape card info from pokemon-card.com

    April 23, 2024 by Weihang
"""

from CardScraperJP import CardScraperJP
import logging

MODE = "DEBUG"
MODE = "BUILD"

logging.basicConfig(
    filename="logs/log_file.log" if MODE == "DEBUG" else "logs/scrape_jp_log.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG if MODE == "DEBUG" else logging.INFO,
)

logger = logging.getLogger(__name__)


redo_list = [7008, 7009, 7013, 32295, 32318, 36704, 36903, 37194, 37371, 37396]

scraper = CardScraperJP()
if MODE == "BUILD":
    # NOTE: assign_task() is referenced in the upstream history but is not
    # defined on CardScraperJP or CardScraper. Do not uncomment it.
    # scraper.assign_task(44944, 45843, overwrite=True)
    #
    # explore_range is the run-length of consecutive misses tolerated before
    # update() gives up; the window only extends on a hit.
    #
    # The 2026-09-18 backfill needed 3000 to cross the ~2,470-id gap left by
    # upstream going quiet in Sep 2025. That was one-off. Routine runs start
    # at the high-water mark with new cards appearing contiguously, so 100 is
    # ample -- and it costs at most 100 wasted requests per run rather than
    # 3,000. Raise it again only for another long backfill.
    scraper.update(explore_range=100)
if MODE == "DEBUG":
    scraper.read_card(45806)
    # for card in redo_list:
    #     scraper.read_card(card)
