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

    def read_text(self, p):
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

        ## Required
        card.set_jp_id(card_id)
        logger.info(f"card id: {card.jp_id}")

        card.set_url(self.get_url(card_id))
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        card_page = bs4.BeautifulSoup(content, "html.parser").section

        card.set_name(self.read_text(card_page.h1))
        logger.debug(f"name: {card.name}")

        img = card_page.find("img", class_="fit")["src"]
        card.set_img(self.complete_url(img))
        logger.debug(f"img: {card.img}")

        card_type = card_page.h2.get_text().strip()
        non_pokemon_types = [
            "基本エネルギー",
            "特殊エネルギー",
            "サポート",
            "グッズ",
            "ポケモンのどうぐ",
            "スタジアム",
        ]
        pokemon_types = ["特性", "ワザ", "進化", "古代能力", "GXワザ"]
        if card_type in non_pokemon_types:
            card.set_card_type(card_type)
            for p_tag in card_page.h2.find_next_siblings("p"):
                text = p_tag.text.strip()
                if not text.startswith(card_type + "は") and not text.startswith(
                    "グッズは"
                ):
                    card.set_effect(self.read_text(card_page.find("p")))
                    logger.debug(f"effect: {card.effect}")

        elif card_type in pokemon_types:
            card.set_card_type("Pokémon")
        else:
            logger.error(f"unknown card type: {card_type}")
        logger.debug(f"card type (raw) : {card_type}")
        logger.debug(f"card type (read): {card.card_type}")

        ## Optional
        set_info = card_page.find("img", class_="img-regulation")
        if set_info:
            set_name = set_info["alt"]
            set_img = set_info["src"]
            card.set_set(set_name, self.complete_url(set_img))
            logger.debug(f"set: {card.set_name}, {card.set_img}")

        collector_info = card_page.find("div", class_="subtext").get_text().strip()
        if collector_info:
            pattern = r"(\d+|\w+)\s*/\s*(\w+-?\w+|\d+)"
            matches = re.match(pattern, collector_info)
            if matches:
                number = matches.group(1)
                total = matches.group(2)
                logger.debug(f"number: {number}")
                logger.debug(f"total: {total}")
            else:
                number = collector_info
                total = -1
                logger.debug(f"number: {number}")
                logger.warn("No total")
            card.set_collector(number, total)

        rarity_info = card_page.find("img", width="24")
        if rarity_info:
            rarity_img = rarity_info["src"]
            rarity = rarity_img.split(".")[0].split("ic_")[1]
            card.set_rarity(rarity, self.complete_url(rarity_img))
            logger.debug(f"rarity: {card.rarity}, {card.rarity_img}")

        author_info = card_page.find("div", class_="author").get_text().strip()
        if author_info:
            author = author_info.split("\n")[1]
            card.set_author(author)
            logger.debug(f"author: {card.author}")

        for h2_tag in card_page.find_all("h2"):
            if h2_tag.text.strip() == "特別なルール":
                for p_tag in h2_tag.find_next_siblings("p"):
                    rule_box = self.read_text(p_tag)
                    card.set_rule_box(rule_box)
                    logger.debug(f"rule box: {card.rule_box}")
                    logger.debug(f"tags: {card.tags}")

        ## Only for Pokémon

        pokedex_info = card_page.find("div", class_="card")
        if pokedex_info:
            if pokedex_info.h4:
                dexline = pokedex_info.h4.get_text().strip().split("\u3000")
                if len(dexline) == 2:
                    [dexNum, dexClass] = dexline
                    dexNum = int(dexNum.split(".")[1])
                    card.set_pokedex(dexNum, dexClass)
                elif len(dexline) == 1:
                    if any(char.isdigit() for char in dexline[0]):
                        dexNum = dexline[0]
                        card.set_pokedex(num=dexNum)
                    else:
                        dexClass = dexline[0]
                        card.set_pokedex(category=dexClass)
                logger.debug(f"pokedex: {card.pokedex_number}, {card.pokemon_category}")

            if len(pokedex_info.find_all("p")) == 2:
                htAndWt = pokedex_info.p.get_text().split("：")
                height = float(htAndWt[1].split(" ")[0])
                weight = float(htAndWt[2].split(" ")[0])
                dexDesc = pokedex_info.find_all("p")[1].get_text()
                card.set_ht_wt(height, weight)
                logger.debug(f"height: {card.height}, weight: {card.weight}")
                card.set_flavor_text(dexDesc)
                logger.debug(f"flavor: {card.flavor_text}")
            elif (
                len(pokedex_info.find_all("p")) == 1
                and "重さ" in pokedex_info.find("p").get_text()
            ):
                htAndWt = pokedex_info.p.get_text().split("：")
                height = float(htAndWt[1].split(" ")[0])
                weight = float(htAndWt[2].split(" ")[0])
                card.set_ht_wt(height, weight)
                logger.debug(f"height: {card.height}, weight: {card.weight}")
            elif len(pokedex_info.find_all("p")) == 1:
                dexDesc = pokedex_info.find("p").get_text()
                card.set_flavor_text(dexDesc)
                logger.debug(f"flavor: {card.flavor_text}")
