"""
    Scrape card info from Japanese website

    April 24, 2024 by Weihang
"""

import re
import bs4
import time
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
        if t == "none":
            t = "colorless"
        return t.capitalize().strip()

    def read_text(self, p, no_space=False):
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
        if no_space:
            p = p.replace(" ", "")
        return p.strip()

    def find_evolve_from(self, area, card, skip=""):
        name = card.name.replace(skip, "")
        name = name.replace(" ", "")
        a_tag = area.find_next("a")
        last_a_tag = a_tag
        found = False
        while a_tag:
            if self.read_text(a_tag, no_space=True) == name:
                next_a_tag = a_tag.find_next("a")
                while next_a_tag:
                    if next_a_tag.find_next_sibling("div", class_="arrow_off"):
                        card.set_evolve_from(next_a_tag.text.strip())
                        logger.debug(f"evolve from: {card.evolve_from}")
                        found = True
                        break
                    next_a_tag = next_a_tag.find_next("a")
            if not found:
                last_a_tag = a_tag
                a_tag = a_tag.find_next("a")
            else:
                break
        return last_a_tag, found

    def read_card(self, card_id):
        result_code = "Successfully scraped"
        card = Card()

        ## Required
        card.set_jp_id(card_id)
        logger.debug(f"card id: {card.jp_id}")

        card.set_url(self.get_url(card_id))
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        card_page_all = bs4.BeautifulSoup(content, "html.parser")
        card_page = card_page_all.section

        if not card_page:
            # Error: No such card!
            logger.debug(f"Card {card_id} not found!")
            return "Page not found"

        card.set_card_name(self.read_text(card_page.h1))
        logger.debug(f"name: {card.name}")

        img = card_page.find("img", class_="fit")["src"]
        card.set_img(self.complete_url(img))
        logger.debug(f"img: {card.img}")

        tera_info = card_page.find("p", class_="mt20")
        tera_text = "このポケモンは、ベンチにいるかぎり、ワザのダメージを受けない。"
        if tera_info and tera_info.get_text().strip() == tera_text:
            card.set_tera()
            logger.debug(f"tera: {card.tera_effect}")

        card_type = card_page.h2.get_text().strip()
        non_pokemon_types = [
            "基本エネルギー",
            "特殊エネルギー",
            "サポート",
            "グッズ",
            "ポケモンのどうぐ",
            "スタジアム",
            "ワザマシン",
            "トレーナー",  # error: 46029
        ]
        pokemon_types = [
            "特性",
            "ワザ",
            "進化",
            "古代能力",
            "GXワザ",
            "ポケパワー",
            "ポケボディー",
            "どうぐ",
            "きのみ",
        ]
        if card_type in non_pokemon_types:
            card.set_card_type(card_type)

            next_h2 = card_page.h2.find_next("h2")
            p_tags = []
            sibling = card_page.h2.find_next_sibling()
            while sibling and sibling != next_h2:
                if sibling.name == "p":
                    p_tags.append(sibling)
                sibling = sibling.find_next_sibling()
            text = ""
            for p_tag in p_tags:
                if p_tag.find("p"):  # avoid nested p_tags
                    continue
                raw_text = self.read_text(p_tag)
                paragraphs = raw_text.split("\n")
                for para in paragraphs:
                    para = para.strip()
                    if (
                        not para.startswith(card_type + "は")
                        and not para.startswith("グッズは")
                        and para
                    ):
                        text = text + "\n" + para
            if text.strip():
                card.set_effect(text.strip())
                logger.debug(f"effect: {card.effect}")
        elif card_type in pokemon_types:
            card.set_card_type("Pokémon")
        else:
            result_code = "Something wrong"
            logger.error(f"Card {card.jp_id} has unknown card type: {card_type}")
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
                logger.debug("No total")
            card.set_collector(number, total)

        rarity_info = card_page.find("img", width="24")
        if rarity_info:
            rarity_img = rarity_info["src"]
            rarity = rarity_img.split(".")[0].split("ic_")[1]
            card.set_rarity(rarity, self.complete_url(rarity_img))
            logger.debug(f"rarity: {card.rarity}, {card.rarity_img}")

        author_info = card_page.find("div", class_="author").get_text().strip()
        if author_info:
            author = [a for a in author_info.split("\n") if a != "イラストレーター"]
            card.set_author(author)
            logger.debug(f"author: {card.author}")

        ## For Pokémon
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
        stage_info = card_page.find("span", class_="type")
        if stage_info:
            stage = stage_info.get_text().strip()
            if "\xa0" in stage:
                stage = stage.replace("\xa0", " ")
            card.set_stage(stage)
            logger.debug(f"stage: {card.stage}")

        hp_info = card_page.find("span", class_="hp-num")
        if hp_info:
            hp = int(hp_info.get_text().strip())
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")

        level_info = card_page.find("span", class_="level-num")
        if level_info:
            level = level_info.get_text().strip()
            card.set_level(level)
            logger.debug(f"level: {card.level}")

        types_info = card_page.find("div", class_="td-r").find_all(
            "span", class_=lambda x: "icon" in x
        )
        if types_info:
            types = [self.format_type(l["class"][0].split("-")[1]) for l in types_info]
            card.set_types(types)
            logger.debug(f"types: {card.types}")

        # Attack part
        if card.card_type == "Pokémon":
            part = (
                content.split('<span class="hp-type">タイプ</span>')[1]
                .split('<div class="clear">')[0]
                .strip()
            )
        else:
            part = (
                content.split('<div class="TopInfo Text-fjalla">')[1]
                .split('<div class="clear">')[0]
                .strip()
            )

        soup = bs4.BeautifulSoup(part, features="html.parser")
        attack_part = bs4.BeautifulSoup(
            soup.prettify(formatter="minimal"), features="html.parser"
        )

        for area in attack_part.find_all("h2"):
            area_name = area.get_text().strip()
            if area_name == "ワザマシン":
                card.set_technical_machine(self.read_text(area.find_next("p")))
                logger.debug(f"technical machine rule: {card.technical_machine_rule}")
                continue
            if area_name == "特性":
                ability_name = area.find_next("h4").get_text().strip()
                ability_effect = self.read_text(area.find_next("p"))
                card.add_ability(ability_name, ability_effect)
                logger.debug(
                    f"ability [{card.abilities[-1]["name"]}]: {card.abilities[-1]["effect"]}"
                )
                continue
            if area_name == "古代能力":
                trait_name = area.find_next("h4").get_text().strip()
                trait_effect = self.read_text(area.find_next("p"))
                card.set_ancient_trait(trait_name, trait_effect)
                logger.debug(
                    f"ancient trait [{card.ancient_trait["name"]}]: {card.ancient_trait["effect"]}"
                )
                continue
            if area_name == "ポケパワー":
                poke_power_name = area.find_next("h4").get_text().strip()
                poke_power_effect = self.read_text(area.find_next("p"))
                card.set_poke_power(poke_power_name, poke_power_effect)
                logger.debug(
                    f"poke power [{card.poke_power["name"]}]: {card.poke_power["effect"]}"
                )
                continue
            if area_name == "ポケボディー":
                poke_body_name = area.find_next("h4").get_text().strip()
                poke_body_effect = self.read_text(area.find_next("p"))
                card.set_poke_body(poke_body_name, poke_body_effect)
                logger.debug(
                    f"poke body [{card.poke_body["name"]}]: {card.poke_body["effect"]}"
                )
                continue
            if area_name == "どうぐ":
                item = area.find_next("h4").get_text().strip()
                item_effect = self.read_text(area.find_next("p"))
                card.set_held_item(item, item_effect)
                logger.debug(
                    f"held item [{card.held_item["item"]}]: {card.held_item["effect"]}"
                )
                continue
            if area_name == "きのみ":
                berry = area.find_next("h4").get_text().strip()
                berry_effect = self.read_text(area.find_next("p"))
                card.set_held_berry(berry, berry_effect)
                logger.debug(
                    f"held berry [{card.held_berry["berry"]}]: {card.held_berry["effect"]}"
                )
                continue
            if area_name in ["ワザ", "GXワザ"]:
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
                            attack_cost.append(
                                self.format_type(span_tag["class"][0].split("-")[1])
                            )
                        else:
                            attack_damage = self.read_attack_damage(
                                span_tag.get_text().strip()
                            )
                    attack_name = attack.get_text().strip().split(" ")[0].strip()
                    attack_effect = self.read_text(attack.find_next("p"))
                    card.add_attack(
                        attack_cost, attack_name, attack_damage, attack_effect
                    )
                    logger.debug(
                        f"attack [{card.attacks[-1]["name"]}]: {card.attacks[-1]["cost"]}: {card.attacks[-1]["damage"]}: {card.attacks[-1]["effect"]}"
                    )
                continue
            if area_name == "VSTARパワー":
                vstar_type = area.find_next("h4").get_text().strip()
                vstar_name = area.find_next("h4").find_next("h4")
                vstar_effect = self.read_text(area.find_next("p"))
                if vstar_type == "特性":
                    card.set_vstar_power_ability(
                        vstar_name.get_text().strip(), vstar_effect
                    )
                    logger.debug(f"VSTAR power: {card.vstar_power}")
                elif vstar_type == "ワザ":
                    vstar_cost = []
                    vstar_damage = None
                    for span_tag in vstar_name.find_all("span"):
                        if "icon" in str(span_tag):
                            vstar_cost.append(
                                self.format_type(span_tag["class"][0].split("-")[1])
                            )
                        else:
                            vstar_damage = self.read_attack_damage(
                                span_tag.get_text().strip()
                            )
                    vstar_name = vstar_name.get_text().strip().split(" ")[0].strip()
                    card.set_vstar_power_attack(
                        vstar_cost, vstar_name, vstar_damage, vstar_effect
                    )
                    logger.debug(f"VSTAR power: {card.vstar_power}")
                else:
                    result_code = "Something wrong"
                    logger.error(
                        f"{card.jp_id} has an unseen VSTAR power type: {vstar_type}!!"
                    )
                continue
            if area_name == "特別なルール":
                for p_tag in area.find_next_siblings("p"):
                    rule_box = self.read_text(p_tag)
                    card.set_rule_box(rule_box)
                    logger.debug(f"rule box: {card.rule_box}")
                    logger.debug(f"tags: {card.tags}")
                continue
            if area_name in non_pokemon_types:
                # already handled above
                continue
            if area_name == "進化":
                if card.stage != "たね":
                    last_a_tag, found = self.find_evolve_from(area, card)

                    if not found:
                        p_tag = last_a_tag.find_next("p")
                        if p_tag:
                            if p_tag.find_next_sibling("div", class_="arrow_off"):
                                card.set_evolve_from(p_tag.text.strip())
                                logger.debug(f"evolve from: {card.evolve_from}")
                                found = True

                    if not found:
                        # Error on page
                        if last_a_tag.find_next_sibling("div", class_="arrow_on"):
                            card.set_evolve_from(last_a_tag.text.strip())
                            logger.warn(
                                f"Card {card.jp_id} evolve from: {card.evolve_from}?"
                            )
                            found = True

                    if not found:
                        # LV.X Pokemon
                        if (
                            card.stage == "レベルアップ"
                            and card.level == "X"
                            and "LV.X" not in card.name
                        ):
                            card.set_card_name(card.name + " LV.X")
                            logger.debug(f"updated card name to: {card.name}")
                            last_a_tag, found = self.find_evolve_from(area, card)

                    if not found:
                        # some ex, GX pokemon
                        suffixes = ["ex", "GX"]
                        for word in suffixes:
                            if word in card.name:
                                last_a_tag, found = self.find_evolve_from(
                                    area, card, skip=word
                                )

                    if not found:
                        # fossil Pokemon
                        if len(area.find_all_next("a")) == 1:
                            card.set_evolve_from(area.find_next("a").text.strip())
                            logger.debug(
                                f"Card {card.jp_id} evolve from: {card.evolve_from}"
                            )
                            found = True

                    if not found:
                        result_code = "Something wrong"
                        logger.error(
                            f"Card {card.jp_id} has trouble finding 'evolve from'!"
                        )
                continue

            result_code = "Something wrong"
            logger.error(f"{card.jp_id} has an unseen areaType: {area_name}!!")

        td = attack_part.find_all("td")
        if len(td) > 0:
            weak_types = []
            if td[0].find("span"):
                weak_value = td[0].get_text().strip()
                for span_tag in td[0].find_all("span"):
                    weak_types.append(
                        self.format_type(span_tag["class"][0].split("-")[1])
                    )
            else:
                weak_value = None
            card.set_weakness(weak_types, weak_value)
            logger.debug(f"weak: {card.weakness}")

        if len(td) > 1:
            resist_types = []
            if td[1].find("span"):
                resist_value = td[1].get_text().strip()
                for span_tag in td[1].find_all("span"):
                    resist_types.append(
                        self.format_type(span_tag["class"][0].split("-")[1])
                    )
            else:
                resist_value = None
            card.set_resistance(resist_types, resist_value)
            logger.debug(f"resist: {card.resistance}")

        if len(td) > 2:
            retreat = len(td[2].find_all("span"))
            card.set_retreat(retreat)
            logger.debug(f"retreat: {card.retreat}")

        link_info = card_page_all.find_all("li", class_="List_item")
        if link_info:
            for li_tag in link_info:
                a_tag = li_tag.find("a", class_="Link Link-arrow")
                if a_tag:
                    link_url = self.complete_url(a_tag.get("href"))
                else:
                    link_url = None
                card.add_source(li_tag.get_text().strip(), link_url)
                logger.debug(
                    f"source: [{card.sources[-1]["name"]}]({card.sources[-1]["link"]})"
                )

        card.save()
        del card
        return result_code

    def update(self, explore_range=10):
        """
        Download the newest cards

        """
        logger.info("===== Updating started (jp) =====")

        downloaded_list = self.get_downloaded_id_list(lang="jp")
        last_downloaded = max(downloaded_list)
        logger.info(f"Last downloaded card is {last_downloaded}.")

        card_id = last_downloaded + 1
        scraped_list, question_list = [], []
        max_explore = last_downloaded + explore_range

        while card_id <= max_explore:
            code = self.read_card(card_id)
            if code == "Successfully scraped":
                scraped_list.append(card_id)
                max_explore = card_id + explore_range
            elif code == "Something wrong":
                question_list.append(card_id)
            elif code == "Page not found":
                pass
            else:
                logger.error(f"Card {card_id} has unseen result code: {code}")

            if card_id % 100 == 0:
                time.sleep(10)

            card_id += 1

        self.save_list_to_file(scraped_list, "logs/scraped_jp_id_list.txt")
        self.save_list_to_file(question_list, "logs/question_jp_id_list.txt")
        if scraped_list:
            self.upadte_readme(max(scraped_list))
        logger.info(
            f"Searched {card_id - last_downloaded} cards; checked up to card {card_id}."
        )
