"""
    Scrape card info from Traditional Chinese (Taiwan) website

    Februray 25, 2025 by Weihang
"""

import bs4
import time
import logging

from Card import Card
from CardScraper import CardScraper

logger = logging.getLogger(__name__)


class CardScraperTC(CardScraper):
    def get_url(self, card_id):
        return f"https://asia.pokemon-card.com/tw/card-search/detail/{card_id}/"

    def extract_energy(self, url):
        """
        Get the Energy from the energy image url

        """
        return url.split(".png")[0].split("/")[-1]

    def format_set_name(self, s):
        if s != -1 and len(s) >= 3 and not s[1].isdigit():
            return s[:2].upper() + s[2:]
        return str(s)

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

    def process_skill(self, card, focus, just_skill=False):
        vstar_skill = False
        if just_skill:
            array = focus
        else:
            array = focus.find_all("div", class_="skill")
        for skill in array:
            name = skill.find("span", class_="skillName").get_text(strip=True)
            skill_effect = skill.find("p", class_="skillEffect").get_text(strip=True)
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
                if any(word in name for word in ["支援者", "物品", "道具", "競技場"]):
                    logger.error(f"This attack has a Trainer rule: {card.card_type}")
                    self.result_code = "Something wrong"
                elif skill_effect:
                    card.set_rule_box(skill_effect)
                    logger.debug(f"rule box: {card.rule_box}")
                    logger.debug(f"tags: {card.tags}")
                else:
                    if "ex" in name:
                        card.set_ex_rule_tc()
                        logger.debug(f"rule box: {card.rule_box}")
                        logger.debug(f"tags: {card.tags}")
                    else:
                        logger.error(f"Unseen rule box {name}")
                        self.result_code = "Something wrong"

            elif "V-UNION放置方法" in name:
                continue
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

    def get_attacks_or_effects(self, card, card_page):
        focus = card_page.find("div", class_="skillInformation")
        category = focus.find("h3").get_text(strip=True)
        if category == "招式":
            if card.card_type != "Pokémon":
                logger.error(f"This card has 招式 but has card type: {card.card_type}")
                self.result_code = "Something wrong"

            self.process_skill(card, focus)

            if "ex" in card.name and "ex" not in card.tags:
                card.set_ex_rule_tc()
                logger.debug(f"rule box: {card.rule_box}")
                logger.debug(f"tags: {card.tags}")

        else:
            # Trainer cards
            card.set_card_type(category)
            logger.debug(f"card type: {card.card_type}")

            # Get effect
            skill_list = [
                s
                for s in card_page.find_all("div", class_="skill")
                if "規則" not in s.find("span", class_="skillName").get_text()
            ]
            effect_text = (
                skill_list[0].find("p", class_="skillEffect").get_text(strip=True)
            )
            card.set_effect(effect_text.strip())
            logger.debug(f"effect: {card.effect}")
            if len(skill_list) > 1:
                self.process_skill(card, skill_list[1:], just_skill=True)

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
            collector = focus.find("span", class_="collectorNumber").get_text(
                strip=True
            )
            collector_series = collector.split(" ")[0].split("/")
            logger.debug(collector_series)
            if len(collector_series) == 2:
                number, total = collector_series
            elif len(collector_series) == 1:
                number = collector_series[0]
                total = -1
            else:
                logger.error(f"number/total can't identified: {collector_series}")
                self.result_code = "Something wrong"
            card.set_collector(number, total)
            logger.debug(f"number: {card.number} out of {card.set_total}")

            set_img = focus.find("span", class_="expansionSymbol").find("img")["src"]
            set_name = set_img.split("mark/")[-1]
            if "twhk_exp_" in set_name:
                set_name = set_name.split("twhk_exp_")[-1].split(".png")[0]
            elif "twhk_" in set_name:
                set_name = set_name.split("twhk_")[-1].split("_")[0]
            elif "SM_" in set_name:
                set_name = (
                    set_name.split("mark_")[-1]
                    .split("expantion_")[-1]
                    .split("OUT")[0]
                    .split("Out")[0]
                    .split("out")[0]
                    .split(".png")[0]
                )
                set_name = set_name[:2].upper() + set_name[2:]
                set_name = set_name.split("_")[0]
            elif "mark_expantion_" in set_name:
                set_name = set_name.split("mark_expantion_")[-1].split(".png")[0]
            elif "PROMO" in set_name:
                set_name = card.set_total
            elif "@" in set_name:
                set_name = set_name.split("@")[0]
            else:
                set_name = set_name.split("_")[0]
            if isinstance(set_name, str):
                set_name = set_name.split("_F")[0]
            card.set_set(self.format_set_name(set_name), set_img)
            logger.debug(f"set: {card.set_name}, {card.set_img}")

            mark = focus.find("span", class_="alpha").get_text(strip=True)
            card.set_mark(mark)
            logger.debug(f"regulation: {card.regulation}")

            card.set_out_id(card.set_name + "-" + card.number)

        expansion = page.find("section", class_="expansionLinkColumn")
        if expansion:
            set_full_name = expansion.find("a").get_text(strip=True)
            card.set_set_full_name(set_full_name)
            logger.debug(f"set full name: {card.set_full_name}")

    def get_author(self, card, page):
        focus = page.find("div", class_="illustrator")
        if focus:
            author = [a.get_text(strip=True) for a in focus.find_all("a")]
            if author != ["n/a"]:
                card.set_author(author)
                logger.debug(f"author: {card.author}")

    def get_evolution(self, card, page):
        focus = page.find("div", class_="evolution")
        evolves_from = None
        if focus:
            ul = focus.find("ul")
            evolve_found = False
            previous = []
            current = []
            while ul:
                li_list = ul.find_all("li", recursive=False)
                for li in li_list:
                    ul = li.find("ul")
                    if ul:
                        break
                    if "active" in li.get("class"):
                        evolves_from = previous[:]
                        evolve_found = True
                        break
                    current.append(li.get_text(strip=True))

                if evolve_found:
                    break

                previous = current[:]
                current = []

            if evolves_from:
                card.set_evolve_from(evolves_from)
                logger.debug(f"evolve from: {card.evolve_from}")

    def get_pokedex_flavor(self, card, page):
        focus = page.find("div", class_="extraInformation")
        if focus:
            h3 = focus.find("h3")
            if h3:
                dexline = h3.get_text(strip=True).split(" ")
                if len(dexline) == 2:
                    dexNum, dexClass = dexline
                    card.set_pokedex(dexNum.split(".")[-1], dexClass)
                elif len(dexline) == 1:
                    if any(char.isdigit() for char in dexline[0]):
                        dexNum = dexline[0].split(".")[-1]
                        card.set_pokedex(num=dexNum)
                    else:
                        dexClass = dexline[0]
                        card.set_pokedex(category=dexClass)
                logger.debug(f"pokedex: {card.pokedex_number}, {card.pokemon_category}")

            # height, weight, flavor
            size = focus.find("p", class_="size")
            if size.find("span"):
                height, weight = size.find_all("span", class_="value")
                card.set_ht_wt(height.get_text(strip=True), weight.get_text(strip=True))
                logger.debug(f"height: {card.height}, weight: {card.weight}")

            flavor = focus.find("p", class_="discription")
            if flavor:
                card.set_flavor_text(flavor.get_text(strip=True).replace("\n", ""))
                logger.debug(f"flavor: {card.flavor_text}")

    def read_card(self, web_id):
        self.result_code = "Successfully scraped"
        card = Card()
        card.set_lang("tc")

        card.set_url(self.get_url(web_id))
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        soup = bs4.BeautifulSoup(content, "html.parser")

        card_page = soup.find("div", class_="wrapper")
        if (
            card_page.find("h1", class_="pageHeader").get_text(strip=True)
            == "卡牌搜尋結果"
        ):
            logger.error(f"Card id {web_id} not found!")
            self.result_code = "Page not found"
        else:
            self.get_name_stage(card, card_page)
            self.get_img_url(card, card_page)
            self.get_hp_types(card, card_page)
            self.get_attacks_or_effects(card, card_page)
            self.get_weak_resist_retreat(card, card_page)
            self.get_set_regu_collect(card, card_page)
            self.get_author(card, card_page)
            self.get_evolution(card, card_page)
            self.get_pokedex_flavor(card, card_page)
            card.save()

        del card
        return self.result_code

    def update(self, explore_range=10):
        """
        Download the newest cards

        """
        logger.info("===== Updating started (tc) =====")

        downloaded_list = self.get_downloaded_id_list(lang="tc")
        last_downloaded = max(downloaded_list) if downloaded_list else 1
        logger.info(f"Last downloaded card is {last_downloaded}.")

        card_id = last_downloaded + 1
        scraped_list, question_list, missing_list = [], [], []
        max_explore = last_downloaded + explore_range

        while card_id <= max_explore:
            code = self.read_card(card_id)
            if code == "Successfully scraped":
                scraped_list.append(card_id)
                max_explore = card_id + explore_range
            elif code == "Something wrong":
                question_list.append(card_id)
            elif code == "Page not found":
                missing_list.append(card_id)
            else:
                logger.error(f"Card {card_id} has unseen result code: {code}")
                self.result_code = "Something wrong"

            if card_id % 200 == 0:

                self.save_list_to_file(scraped_list, "logs/scraped_tc_id_list.txt")
                self.save_list_to_file(question_list, "logs/question_tc_id_list.txt")
                self.save_list_to_file(missing_list, "logs/missing_tc_id_list.txt")
                if scraped_list:
                    self.upadte_readme(max(scraped_list), lang="tc")
                logger.info(
                    f"Searched {card_id - last_downloaded} cards; checked up to card {card_id}."
                )

                time.sleep(10)

            card_id += 1

        # self.save_list_to_file(scraped_list, "logs/scraped_tc_id_list.txt")
        # self.save_list_to_file(question_list, "logs/question_tc_id_list.txt")
        # self.save_list_to_file(missing_list, "logs/missing_tc_id_list.txt")
        # if scraped_list:
        #     self.upadte_readme(max(scraped_list), lang="tc")
        # logger.info(
        #     f"Searched {card_id - last_downloaded} cards; checked up to card {card_id}."
        # )
