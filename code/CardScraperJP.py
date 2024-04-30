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
    
    def format_type(self, t):
        if t == 'none':
            t = 'colorless'
        return t.capitalize().strip()

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
                    marks.append(self.format_type(span["class"][0].split("-")[1]))
                elif "mega" in str(span):
                    marks.append(span["class"][1].split("-")[1][:4])
                elif "prismstar" in str(span):
                    marks.append(span["class"][1].split("-")[1])

            for i in range(len(marks)):
                p = str(p).replace(str(spans[i]), marks[i])
            p = bs4.BeautifulSoup(p, "html.parser")
        p = p.get_text().replace("\n ", "")
        return p.strip()

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
                if p_tag.find("p"):
                    continue
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
        # TODO: handle V-UNION cards
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
                height = htAndWt[1].split("\u3000")[0].strip()
                weight = htAndWt[2].strip()
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
                height = htAndWt[1].split("\u3000")[0].strip()
                weight = htAndWt[2].strip()
                card.set_ht_wt(height, weight)
                logger.debug(f"height: {card.height}, weight: {card.weight}")
            elif len(pokedex_info.find_all("p")) == 1:
                dexDesc = pokedex_info.find("p").get_text()
                card.set_flavor_text(dexDesc)
                logger.debug(f"flavor: {card.flavor_text}")

        # Right box
        stage_info = card_page.find('span', class_='type')
        if stage_info:
            stage = stage_info.get_text().strip()
            if '\xa0' in stage:
                stage = stage.replace('\xa0', ' ')
            card.set_stage(stage)
            logger.debug(f"stage: {card.stage}")

        hp_info = card_page.find('span', class_='hp-num')
        if hp_info:
            hp = int(hp_info.get_text().strip())
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")

        level_info = card_page.find('span', class_='level-num')
        if level_info:
            level = int(level_info.get_text().strip())
            card.set_level(level)
            logger.debug(f"level: {card.level}")

        types_info = card_page.find('div', class_='td-r').find_all('span', class_=lambda x: 'icon' in x)
        if types_info:
            types = [self.format_type(l['class'][0].split('-')[1]) for l in types_info]
            card.set_types(types)
            logger.debug(f"types: {card.types}")


        # Attack part
        if card.card_type == "Pokémon":
            part = (
                content.split('<span class="hp-type">タイプ</span>')[1]
                .split('<div class="clear">')[0]
                .strip()
            )
            soup = bs4.BeautifulSoup(part, features="html.parser")
            attack_part = bs4.BeautifulSoup(soup.prettify(formatter="minimal"), features="html.parser")

            for area in attack_part.find_all("h2"):
                area_name = area.get_text().strip()
                if area_name == "特性":
                    ability_name = area.find_next("h4").get_text().strip()
                    ability_effect = self.read_text(area.find_next("p"))
                    card.add_ability(ability_name, ability_effect)
                    logger.debug(f"ability [{card.abilities[-1]["name"]}]: {card.abilities[-1]["effect"]}")
                    continue
                if area_name == "古代能力":
                    trait_name = area.find_next("h4").get_text().strip()
                    trait_effect = self.read_text(area.find_next("p"))
                    card.set_ancient_trait(trait_name, trait_effect)
                    logger.debug(f"ancient trait [{card.ancient_trait["name"]}]: {card.ancient_trait["effect"]}")
                    continue
                if area_name == "GXワザ":
                    continue
                if area_name == "VSTARパワー":
                    continue

                if area_name == "ワザ":
                    next_h2 = area.find_next("h2")
                    h4_tags = []
                    sibling = area.find_next_sibling()
                    while sibling and sibling != next_h2:
                        if sibling.name == "h4":
                            h4_tags.append(sibling)
                        sibling = sibling.find_next_sibling()                    
                    for attack in h4_tags:
                        attack_cost = []
                        attack_damage = None
                        for span_tag in attack.find_all("span"):
                            if "icon" in str(span_tag):
                                attack_cost.append(self.format_type(span_tag["class"][0].split("-")[1]))
                            else:
                                attack_damage = self.read_attack_damage(span_tag.get_text().strip())
                        attack_name = attack.get_text().strip().split(' ')[0].strip()
                        attack_effect = self.read_text(attack.find_next("p"))
                        card.add_attack(attack_cost,attack_name, attack_damage, attack_effect)
                        logger.debug(f"attack [{card.attacks[-1]["name"]}]: {card.attacks[-1]["cost"]}: {card.attacks[-1]["damage"]}: {card.attacks[-1]["effect"]}")
                    continue
                if area_name == "特別なルール":
                    # already handled above
                    continue
                if area_name == "進化":
                    if card.stage != "たね":
                        a_tag = area.find_next("a")
                        found = False
                        while a_tag:
                            if a_tag.text.strip() == card.name:
                                next_a_tag = a_tag.find_next("a")
                                while next_a_tag:
                                    if next_a_tag.find_next_sibling("div", class_="arrow_off"):
                                        card.set_evolve_from(next_a_tag.text.strip())
                                        logger.debug(f"evolve from: {card.evolve_from}")
                                        found = True
                                        break
                                    next_a_tag = next_a_tag.find_next("a")
                            if not found:
                                a_tag = a_tag.find_next("a")
                            else:
                                break
                    continue
                logger.error(f"{card.jp_id} has an unseen areaType: {area_name}!!")

            ## TODO: weakness table
            ## TODO: set source
