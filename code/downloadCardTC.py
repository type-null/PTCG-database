"""
Download Traditional Chinese card info from asia.pokemon-card.com

Februray 25, 2025 by Weihang
"""

from CardScraperTC import CardScraperTC
import logging

MODE = "DEBUG"
MODE = "BUILD"

logging.basicConfig(
    filename="logs/log_file.log" if MODE == "DEBUG" else "logs/scrape_tc_log.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG if MODE == "DEBUG" else logging.INFO,
)

logger = logging.getLogger(__name__)

scraper = CardScraperTC()

if MODE == "BUILD":
    scraper.update()
if MODE == "DEBUG":
    # card_id = 7143
    # scraper.read_card(card_id)
    scraper.update(explore_range=50)
