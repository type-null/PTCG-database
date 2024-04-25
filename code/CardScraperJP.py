"""
    Scrape card info from Japanese website

    April 24, 2024 by Weihang
"""

import bs4
import sys
import logging

from Card import Card
from CardScraper import CardScraper

logger = logging.getLogger(__name__)


class CardScraperJP(CardScraper):
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

        card.set_id(card_id)
        logger.debug(f"card id: {card.id}")

        card.set_url(self.get_url(card_id))
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        card_page = bs4.BeautifulSoup(content, "html.parser").section

        card.set_name(self.get_name(card_page.h1))
        logger.debug(f"name: {card.name}")

        img = card_page.find("img", class_="fit")["src"]
        card.set_img("https://www.pokemon-card.com" + img)
        logger.debug(f"img: {card.img}")
