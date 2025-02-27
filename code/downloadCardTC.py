"""
    Download Traditional Chinese card info from asia.pokemon-card.com

    Februray 25, 2025 by Weihang
"""

from CardScraperTC import CardScraperTC
import logging

MODE = "DEBUG"
# MODE = "BUILD"

logging.basicConfig(
    filename="logs/log_file.log" if MODE == "DEBUG" else "logs/scrape_tcn_log.log",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    level=logging.DEBUG if MODE == "DEBUG" else logging.INFO,
)

logger = logging.getLogger(__name__)

scraper = CardScraperTC()

if MODE == "BUILD":
    scraper.update()
if MODE == "DEBUG":

    # card_link = (
    #     "https://asia.pokemon-card.com/tw/card-search/detail/12492/"  # 奇樹的電肚蛙ex
    # )
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/12562/" # 扣殺能量
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/12315/"  # 厄鬼椪 碧草面具ex
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/12489/" # 奇樹的頑皮雷彈
    card_link = "https://asia.pokemon-card.com/tw/card-search/detail/7114/"
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/8379/"  # 密勒頓ex
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/8735/"
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/2998/"
    # card_link = "https://asia.pokemon-card.com/tw/card-search/detail/3485/"
    scraper.read_card(card_link)
    # scraper.scrape_set("legendary-collection")
