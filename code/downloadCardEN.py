"""
    Download card info from pkmncards.com

    May 29, 2024 by Weihang
"""

from CardScraperEN import CardScraperEN
import logging

MODE = "DEBUG"
MODE = "BUILD"

logging.basicConfig(
    filename="logs/log_file.log" if MODE == "DEBUG" else "logs/scrape_en_log.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG if MODE == "DEBUG" else logging.INFO,
)

logger = logging.getLogger(__name__)

scraper = CardScraperEN()

if MODE == "BUILD":
    scraper.update()
if MODE == "DEBUG":
    card_link = "https://pkmncards.com/set/miscellaneous/"
    scraper.read_card(card_link)
    # scraper.scrape_set("legendary-collection")
