"""
    Scrape card info from pokemon-card.com

    April 23, 2024 by Weihang
"""

from CardScraperJP import CardScraperJP
import logging

logging.basicConfig(
    filename="log_file.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG,
)

logger = logging.getLogger(__name__)

scraper = CardScraperJP()
scraper.read_card(33406)
