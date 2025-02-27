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

            vstar_skill = False
            for skill in focus.find_all("div", class_="skill"):
                name = skill.find("span", class_="skillName").get_text(strip=True)
                skill_effect = skill.find("p", class_="skillEffect").get_text(
                    strip=True
                )
                if "[VSTAR力量]" in name:
                    vstar_skill = True

                if "[特性]" in name:
                    ability_name = name.split("[特性]")[-1]
                    if vstar_skill:
                        card.set_vstar_power_ability(ability_name, skill_effect)
                        logger.debug(f"VSTAR power: {card.vstar_power}")
                    else:
                        card.add_ability(ability_name, skill_effect)
                        logger.debug(
                            f"ability [{card.abilities[-1]["name"]}]: {card.abilities[-1]["effect"]}"
                        )
                elif "太晶" in name:
                    card.set_tera(lang="tc")
                    logger.debug(f"tera: {card.tera_effect}")
                elif "規則" in name:
                    card.set_rule_box(skill_effect)
                    logger.debug(f"rule box: {card.rule_box}")
                    logger.debug(f"tags: {card.tags}")
                else:
                    attack_cost = [
                        self.extract_energy(e["src"])
                        for e in skill.find("span", class_="skillCost").find_all("img")
                    ]
                    extra = skill.find("span", class_="skillCost").get_text(strip=True)
                    if extra:
                        attack_cost.append(extra)
                    attack_damage = skill.find("span", class_="skillDamage").get_text(
                        strip=True
                    )
                    if vstar_skill:
                        card.set_vstar_power_attack(
                            attack_cost, name, attack_damage, skill_effect
                        )
                        logger.debug(f"VSTAR power: {card.vstar_power}")
                    else:
                        card.add_attack(attack_cost, name, attack_damage, skill_effect)
                        logger.debug(
                            f"attack [{card.attacks[-1]["name"]}]: {card.attacks[-1]["cost"]}: {card.attacks[-1]["damage"]}: {card.attacks[-1]["effect"]}"
                        )

                vstar_skill = False

            if "ex" in card.name and "ex" not in card.tags:
                card.set_ex_rule_tc()
                logger.debug(f"rule box: {card.rule_box}")
                logger.debug(f"tags: {card.tags}")

        else:
            # Trainer cards
            card.set_card_type(category)
            logger.debug(f"card type: {card.card_type}")
            # TODO

    def get_weak_resist_retreat(self, card, page):
        focus = page.find("div", class_="subInformation")
        if focus:
            weak = focus.find("td", class_="weakpoint")
            weak_value = weak.get_text(strip=True)
            if weak_value == "--":
                weak_types = []
                weak_value = None
            else:
                weak_types = [
                    self.extract_energy(e["src"]) for e in weak.find_all("img")
                ]
            card.set_weakness(weak_types, weak_value)
            logger.debug(f"weak: {card.weakness}")

            resist = focus.find("td", class_="resist")
            resist_value = resist.get_text(strip=True)
            if resist_value == "--":
                resist_types = []
                resist_value = None
            else:
                resist_types = [
                    self.extract_energy(e["src"]) for e in resist.find_all("img")
                ]
            card.set_resistance(resist_types, resist_value)
            logger.debug(f"resist: {card.resistance}")

            retreat = focus.find("td", class_="escape")
            card.set_retreat(len(retreat.find_all("img")))
            logger.debug(f"retreat: {card.retreat}")

    def get_set_regu_collect(self, card, page):
        focus = page.find("section", class_="expansionColumn")
        if focus:
            set_img = focus.find("span", class_="expansionSymbol").find("img")["src"]
            set_name = set_img.split("mark/")[-1]
            if "twhk_" in set_name:
                set_name = set_name.split("twhk_")[-1]
            elif "SM_" in set_name:
                set_name = set_name.split("mark_")[-1].split("OUT")[0]
                set_name = set_name[:2].upper() + set_name[2:]
            set_name = set_name.split("_")[0]
            card.set_set(set_name, set_img)
            logger.debug(f"set: {card.set_name}, {card.set_img}")

            mark = focus.find("span", class_="alpha").get_text(strip=True)
            card.set_mark(mark)
            logger.debug(f"regulation: {card.regulation}")

            collector = focus.find("span", class_="collectorNumber").get_text(
                strip=True
            )
            number, total = collector.split("/")
            card.set_collector(number, total)
            logger.debug(f"number: {card.number} out of {card.set_total}")
            card.set_out_id(card.set_name + card.number)

        expansion = page.find("section", class_="expansionLinkColumn")
        if expansion:
            set_full_name = expansion.find("a").get_text(strip=True)
            card.set_set_full_name(set_full_name)
            logger.debug(f"set full name: {card.set_full_name}")

    def get_author(self, card, page):
        focus = page.find("div", class_="illustrator")
        if focus:
            author = [a.get_text(strip=True) for a in focus.find_all("a")]
            card.set_author(author)
            logger.debug(f"author: {card.author}")

    def get_flavor_text(self, card, page):
        focus = page.find("div", class_="extraInformation")
        if focus:
            pass

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
        self.get_weak_resist_retreat(card, card_page)
        self.get_set_regu_collect(card, card_page)
        self.get_author(card, card_page)
        self.get_flavor_text(card, card_page)
