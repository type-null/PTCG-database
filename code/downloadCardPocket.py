"""
Download Pocket card info from limitlesstcg.com

Februray 18, 2025 by Weihang
"""

from CardScraperPocket import CardScraperPocket
import logging

MODE = "DEBUG"
MODE = "BUILD"

logging.basicConfig(
    filename="logs/log_file.log" if MODE == "DEBUG" else "logs/scrape_pocket_log.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG if MODE == "DEBUG" else logging.INFO,
)

logger = logging.getLogger(__name__)

scraper = CardScraperPocket()

if MODE == "BUILD":
    scraper.update()
if MODE == "DEBUG":
    card_link = "https://pocket.limitlesstcg.com/cards/A2/129"
    scraper.read_card(card_link)
    # scraper.scrape_set("legendary-collection")
