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
# ex pokemon: 45729
# tera ex pokemon: 45685
# radiant pokemon: 45294
# tag team pokemon: 37205
# 2 types EX: 37393
# mega EX: 37406
# break pokemon: 33580
# V-UNION: 39921
# VSTAR (ability): 44944
# VSTAR (attack): 42862
# VMAX: 42872
# prism star: 37262
# ancient trait: 30790
# LV.: 1090 (multiple set sources)

# tool: 45786
# tool ( vstar ability): 44058
# tool ( vstar attack): 42183
# tool (attack): 44375, 39730, 31825
# tool (GX attack): 36700, 36898
# tool (team flare): 31982
# old tool: 33278
# ace spec item: 45783


# stadium: 45791

# supporter: 45787

# ace spec energy: 45792
# basic energy in a set: 45440
# basic energy: 8

test_ids = [
    33406,
    45787,
    45729,
    45786,
    45791,
    45792,
    45783,
    45440,
    8,
    33278,
    45685,
    45294,
    37205,
    37393,
    37406,
    33580,
    39921,
    37262,
]


for card_id in test_ids:
    scraper.read_card(card_id)
