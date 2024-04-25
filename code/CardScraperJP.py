"""
    Scrape card info from Japanese website

    April 24, 2024 by Weihang
"""

import re
import bs4
import logging

from Card import Card
from CardScraper import CardScraper

logger = logging.getLogger(__name__)


class CardScraperJP(CardScraper):
    def complete_url(self, url):
        return "https://www.pokemon-card.com" + url

    def get_url(self, card_id):
        return f"https://www.pokemon-card.com/card-search/details.php/card/{card_id}"

    def get_name(self, p):
        """
        <span class="pcg pcg-megamark"></span>
        <span class="pcg pcg-prismstar"></span>
        <span class="icon-psychic icon"></span>

        """
        spans = p.find_all("span")
        marks = []
        if spans:
            for span in spans:
                if "icon" in str(span):
                    marks.append(span["class"][0].split("-")[1])
                elif "mega" in str(span):
                    marks.append(span["class"][1].split("-")[1][:4])
                elif "prismstar" in str(span):
                    marks.append(span["class"][1].split("-")[1])

            for i in range(len(marks)):
                p = str(p).replace(str(spans[i]), marks[i])
            p = bs4.BeautifulSoup(p)
        p = p.get_text().replace("\n   ", "")
        return p

    def read_card(self, card_id):
        card = Card()

        card.set_jp_id(card_id)
        logger.info(f"card id: {card.jp_id}")

        card.set_url(self.get_url(card_id))
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        card_page = bs4.BeautifulSoup(content, "html.parser").section

        card.set_name(self.get_name(card_page.h1))
        logger.debug(f"name: {card.name}")

        img = card_page.find("img", class_="fit")["src"]
        card.set_img(self.complete_url(img))
        logger.debug(f"img: {card.img}")

        card_type = card_page.h2.get_text()
        logger.debug(f"card type (raw): {card_type}")
        if card_type == "基本エネルギー":
            card.set_card_type(card_type)
            return

        set_name = card_page.find("img", class_="img-regulation")["alt"]
        set_img = card_page.find("img", class_="img-regulation")["src"]
        card.set_set(set_name, self.complete_url(set_img))
        logger.debug(f"set: {card.set_name}, {card.set_img}")

        collector = card_page.find("div", class_="subtext").get_text().strip()
        pattern = r"(\d+|\w+)\s*/\s*(\w+-?\w+|\d+)"
        matches = re.match(pattern, collector)
        if matches:
            number = matches.group(1)
            total = matches.group(2)
            logger.debug(f"number: {number}")
            logger.debug(f"total: {total}")
        else:
            number = collector
            total = -1
            logger.debug(f"number: {number}")
            logger.warn("No total")

        rarity_part = card_page.find("img", width="24")
        if rarity_part:
            rarity_img = rarity_part["src"]
            rarity = rarity_img.split(".")[0].split("ic_")[1]
            card.set_rarity(rarity, self.complete_url(rarity_img))
            logger.debug(f"rarity: {card.rarity}, {card.rarity_img}")

        if card_type == "特殊エネルギー":
            card.set_card_type(card_type)
            card.set_effect(self.get_name(card_page.find("p")))
            logger.debug(f"effect: {card.effect}")

            # TODO: need to check "special rule" for special energies
            return
