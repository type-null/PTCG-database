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
    # scraper.assign_task(44944, 45843, overwrite=True)
    scraper.update()
if MODE == "DEBUG":
    scraper.read_card(45806)
    # for card in redo_list:
    #     scraper.read_card(card)
