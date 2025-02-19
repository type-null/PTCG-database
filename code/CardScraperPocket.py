"""
    Scrape TCG Pocket card info from limitlesstcg.com

    Februray 18, 2025 by Weihang
"""

import os
import re
import bs4
import logging
from tqdm import tqdm

from Card import Card
from CardScraper import CardScraper

logger = logging.getLogger(__name__)


class CardScraperPocket(CardScraper):
    letter_to_type = {
        "G": "Grass",
        "R": "Fire",
        "W": "Water",
        "L": "Lightning",
        "P": "Psychic",
        "F": "Fighting",
        "D": "Dark",
        "C": "Colorless",
        "N": "Dragon",
        "0": "No Energy Cost",
        "+": "+",
    }

    def get_img_url(self, card, soup):
        img = soup.find("img", class_="card shadow resp-w")["src"]
        card.set_img(img)
        logger.debug(f"img: {card.img}")

    def read_effect(self, text):
        pattern = r"\[([A-Z0-9+])\]"
        return re.sub(
            pattern,
            lambda m: (
                f" {{{self.letter_to_type[m.group(1)]}}} "
                if m.group(1) in self.letter_to_type and m.group(1) not in {"0", "+"}
                else m.group(0)
            ),
            text,
        )

    def get_name_types_hp(self, card, page):
        texts = page.find("p", class_="card-text-title").get_text(strip=True).split("-")
        name = texts[0]
        card.set_card_name(name)
        logger.debug(f"name: {card.name}")

        if len(texts) > 1:
            types = [t.strip() for t in texts[1].split()]
            card.set_types(types)
            logger.debug(f"types: {card.types}")

        if len(texts) > 2:
            hp = int(texts[2].replace("HP", "").strip())
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")

    def get_type_stage_evolve(self, card, page):
        texts = page.find("p", class_="card-text-type").get_text(strip=True).split("-")
        card_type = texts[0].strip()
        card.set_card_type(card_type)
        logger.debug(f"card type: {card.card_type}")

        if len(texts) > 1:
            stage = texts[1].strip()
            card.set_stage(stage)
            logger.debug(f"stage: {card.stage}")

        if len(texts) > 2:
            match = re.search(r"Evolves from([\w\W]+)", texts[2])
            if match:
                card.set_evolve_from(match.group(1).strip())
                logger.debug(f"evolve from: {card.evolve_from}")

    def get_abilities(self, card, page):
        ability_info_list = page.find_all("div", class_="card-text-ability")
        for ability_info in ability_info_list:
            ability_name = (
                ability_info.find("p", class_="card-text-ability-info")
                .get_text(strip=True)
                .replace("Ability:", "")
                .strip()
            )
            ability_effect = self.read_effect(
                ability_info.find("p", class_="card-text-ability-effect").get_text(
                    strip=True
                )
            )
            card.add_ability(ability_name, ability_effect)
            logger.debug(
                f"ability [{card.abilities[-1]["name"]}]: {card.abilities[-1]["effect"]}"
            )

    def format_costs(self, cost_text):
        costs = []
        for letter in cost_text:
            costs.append(self.letter_to_type[letter])
        return costs

    def get_attacks(self, card, page):
        attack_info_list = page.find_all("div", class_="card-text-attack")
        for attack_info in attack_info_list:
            attack_cost = self.format_costs(
                attack_info.find("span", class_="ptcg-symbol").get_text(strip=True)
            )
            attack_name_info = (
                attack_info.find("p", class_="card-text-attack-info")
                .find_all(string=True, recursive=False)[1]
                .strip()
                .split()
            )
            if re.search(r"\d", attack_name_info[-1]):
                attack_name = " ".join(attack_name_info[:-1])
                attack_damage = attack_name_info[-1]
            else:
                attack_name = " ".join(attack_name_info)
                attack_damage = None

            attack_effect = self.read_effect(
                attack_info.find("p", class_="card-text-attack-effect").get_text(
                    strip=True
                )
            )

            card.add_attack(attack_cost, attack_name, attack_damage, attack_effect)
            logger.debug(
                f"attack [{card.attacks[-1]["name"]}]: {card.attacks[-1]["cost"]}: {card.attacks[-1]["damage"]}: {card.attacks[-1]["effect"]}"
            )

    def get_weak_retreat(self, card, card_page):
        wrr_tag = card_page.find("p", class_="card-text-wrr")
        if wrr_tag:
            wrr_info = wrr_tag.get_text().strip().split("\n")
            weak_types = [
                t.strip()
                for t in wrr_info[0].strip().split()[1:]
                if t.strip() != "none"
            ]
            card.set_weakness(weak_types, "+20")
            logger.debug(f"weak: {card.weakness}")

            card.set_retreat(int(wrr_info[1].strip().split()[1].strip()))
            logger.debug(f"retreat: {card.retreat}")

    def get_author(self, card, card_page):
        author_div = card_page.find("div", class_="card-text-section card-text-artist")
        if author_div:
            author = author_div.find("a").get_text(strip=True)
            card.set_author(author)
            logger.debug(f"author: {card.author}")

    def read_card(self, url):
        card = Card()

        card.set_url(url)
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        soup = bs4.BeautifulSoup(content, "html.parser")

        self.get_img_url(card, soup)

        card_page = soup.find("div", class_="card-text")
        self.get_name_types_hp(card, card_page)
        self.get_type_stage_evolve(card, card_page)
        self.get_abilities(card, card_page)
        self.get_attacks(card, card_page)
        self.get_weak_retreat(card, card_page)
        self.get_author(card, card_page)

        card_print = soup.find("div", class_="card-prints-current")
