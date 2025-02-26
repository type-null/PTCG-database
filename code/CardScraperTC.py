"""
    Scrape card info from Traditional Chinese (Taiwan) website

    Februray 25, 2025 by Weihang
"""

import re
import bs4
import time
import logging
from tqdm import tqdm

from Card import Card
from CardScraper import CardScraper

logger = logging.getLogger(__name__)


class CardScraperTC(CardScraper):
    def extract_energy(self, url):
        """
        Get the Energy from the energy image url

        """
        return url.split(".png")[0].split("/")[-1]

    def get_name_stage(self, card, page):
        focus = page.find("h1", class_="pageHeader cardDetail")
        stage_part = focus.find("span", class_="evolveMarker")
        if stage_part:
            stage = stage_part.get_text(strip=True)
            card.set_stage(stage)
            logger.debug(f"stage: {card.stage}")
            # If it has a stage, then it is a Pokemon card
            card.set_card_type("Pokémon")
            logger.debug(f"card type: {card.card_type}")

        name = "".join(focus.find_all(string=True, recursive=False)).strip()
        card.set_card_name(name)
        logger.debug(f"name: {card.name}")

    def get_img_url(self, card, page):
        img = page.find("div", class_="cardImage").find("img")["src"]
        card.set_img(img)
        logger.debug(f"img: {card.img}")

    def get_hp_types(self, card, card_page):
        focus = card_page.find("p", class_="mainInfomation")
        if focus:
            hp = focus.find("span", class_="number").get_text(strip=True)
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")
            types = [self.extract_energy(img["src"]) for img in focus.find_all("img")]
            card.set_types(types)
            logger.debug(f"types: {card.types}")

    def get_attacks_or_effects(self, card, card_page):
        focus = card_page.find("div", class_="skillInformation")
        category = focus.find("h3").get_text(strip=True)
        if category == "招式":
            if card.card_type != "Pokémon":
                logger.error(f"This card has 招式 but has card type: {card.card_type}")
            # TODO

        else:
            card.set_card_type(category)
            logger.debug(f"card type: {card.card_type}")
            # TODO

    def read_card(self, url):
        card = Card()

        card.set_url(url)
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        soup = bs4.BeautifulSoup(content, "html.parser")

        card_page = soup.find("div", class_="wrapper")
        self.get_name_stage(card, card_page)
        self.get_img_url(card, card_page)
        self.get_hp_types(card, card_page)
        self.get_attacks_or_effects(card, card_page)
