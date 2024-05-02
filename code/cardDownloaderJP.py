"""
    Scrape card info from pokemon-card.com

    April 23, 2024 by Weihang
"""

from CardScraperJP import CardScraperJP
import logging

# MODE = "DEBUG"
MODE = "BUILD"

logging.basicConfig(
    filename="log_file.log" if MODE == "DEBUG" else "scrape_jp_log.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG if MODE == "DEBUG" else logging.INFO,
)

logger = logging.getLogger(__name__)


scraper = CardScraperJP()
scraper.scrape(45800, 45800)
