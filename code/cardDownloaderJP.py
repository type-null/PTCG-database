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

logger.info("\n=========start===========")

scraper = CardScraperJP()

# golisopod: 33406
# supporter: 45787
# ex pokemon: 45729
# item: 45786
# stadium: 45791
# ace spec energy: 45792
# ace spec item: 45783
test_ids = [33406, 45787, 45729, 45786, 45791, 45792, 45783]
for card_id in test_ids:
    scraper.read_card(card_id)
