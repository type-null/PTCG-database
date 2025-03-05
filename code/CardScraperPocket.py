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
        "M": "Metal",
        "N": "Dragon",
        "C": "Colorless",
        "0": "No Energy Cost",
        "+": "+",
    }

    img_to_rarity = {
        "◊": "1 diamond",
        "◊◊": "2 diamond",
        "◊◊◊": "3 diamond",
        "◊◊◊◊": "4 diamond",
        "☆": "1 star",
        "☆☆": "2 star",
        "☆☆☆": "3 star",
        "Crown Rare": "crown",
    }

    def get_img_url(self, card, soup):
        img = soup.find("img", class_="card shadow resp-w")["src"]
        card.set_img(img)
        logger.debug(f"img: {card.img}")

    def read_effect(self, text):
        pattern = r"\[([A-Z0-9+])\]"
        return re.sub(
            r"\.(\S)",
            r". \1",
            re.sub(
                pattern,
                lambda m: (
                    f" {{{self.letter_to_type[m.group(1)]}}} "
                    if m.group(1) in self.letter_to_type
                    and m.group(1) not in {"0", "+"}
                    else m.group(0)
                ),
                text,
            ),
        )

    def get_name_types_hp(self, card, page):
        texts = page.find("p", class_="card-text-title").get_text().split(" -")
        name = texts[0].strip()
        card.set_card_name(name)
        logger.debug(f"name: {card.name}")

        if len(texts) > 1 and "HP" not in texts[1]:
            types = [t.strip() for t in texts[1].split()]
            card.set_types(types)
            logger.debug(f"types: {card.types}")

        if len(texts) > 2:
            hp = int(texts[2].replace("HP", "").strip())
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")
        elif len(texts) > 1 and "HP" in texts[1]:
            hp = int(texts[1].replace("HP", "").strip())
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")

    def get_trainer_text(self, card, page):
        effect_text = self.read_effect(
            page.find_all("div", class_="card-text-section")[1].get_text(strip=True)
        )
        card.set_effect(effect_text.strip())
        logger.debug(f"effect: {card.effect}")

    def get_type_stage_evolve(self, card, page):
        texts = page.find("p", class_="card-text-type").get_text(strip=True).split("-")
        card_type = texts[0].strip()
        card.set_card_type(card_type)
        logger.debug(f"card type: {card.card_type}")

        if card.card_type == "Trainer":
            card_type = texts[1].strip()
            card.set_card_type(card_type)
            logger.debug(f"update card type: {card.card_type}")
            self.get_trainer_text(card, page)
            return

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

    def get_weak_retreat(self, card, page):
        wrr_tag = page.find("p", class_="card-text-wrr")
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

    def get_rule_box(self, card, page):
        wrr_tags = page.find_all("p", class_="card-text-wrr")
        if len(wrr_tags) > 1:
            rule_box = wrr_tags[1].get_text().strip()
            card.set_rule_box(rule_box)
            logger.debug(f"rule box: {card.rule_box}")
        logger.debug(f"tags: {card.tags}")

    def get_author(self, card, page):
        author_div = page.find("div", class_="card-text-section card-text-artist")
        if author_div:
            author = author_div.find("a").get_text(strip=True)
            card.set_author(author)
            logger.debug(f"author: {card.author}")

    def get_set_info(self, card, page):
        set_name = page.find("span", class_="text-lg").get_text().split("(")[0].strip()
        set_code = page.find("img")["alt"]
        set_img_url = page.find("img")["src"]
        card.set_set(set_name, set_img_url)
        card.set_set_code(set_code)
        logger.debug(f"set name: {card.set_name}")
        logger.debug(f"set code: {card.set_code}")
        logger.debug(f"set img: {card.set_img}")

        set_url = "https://pocket.limitlesstcg.com" + page.find("a")["href"]
        content = self.get_content(set_url)
        soup = bs4.BeautifulSoup(content, "html.parser")
        release_info = (
            soup.find("div", class_="infobox-line").get_text().strip().split("•")
        )
        set_total = None
        if len(release_info) > 1:
            date = release_info[0].strip()
            set_total = int(release_info[1].strip().split()[0])
            card.set_set_date(date)
            logger.debug(f"set date: {card.date}")

        collector_info = page.find_all("span")[1].get_text(strip=True).split("·")
        number = collector_info[0].replace("#", "").strip()
        card.set_collector(number, set_total)
        logger.debug(f"number: {card.number} out of {card.set_total}")
        card.set_out_id(card.set_code + "-" + card.number)

        rarity = None
        pack = None
        for info in collector_info[1:]:
            clean_info = info.strip()
            if clean_info in self.img_to_rarity.keys():
                rarity = self.img_to_rarity[clean_info]
            else:
                pack = clean_info.replace("  ", " ")

        if rarity:
            card.set_rarity(rarity)
        else:
            card.set_rarity("promo")
        logger.debug(f"rarity: {card.rarity}")

        if pack:
            card.set_sub_pack(pack)
            logger.debug(f"pack: {card.pack}")

    def read_card(self, url):
        card = Card()
        card.set_game("TCG Pocket")
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
        self.get_rule_box(card, card_page)
        self.get_author(card, card_page)

        card_print = soup.find("div", class_="card-prints-current")
        self.get_set_info(card, card_print)

        card_id = card.out_id

        card.save()
        del card
        return card_id

    def scrape_set(self, set_code):
        set_link = f"https://pocket.limitlesstcg.com/cards/{set_code}/"
        content = self.get_content(set_link)
        soup = bs4.BeautifulSoup(content, "html.parser")
        cards = [
            a["href"] for a in soup.find("div", class_="card-search-grid").find_all("a")
        ]

        for url_tail in tqdm(cards, desc=f"Downloading {set_code}"):
            url = "https://pocket.limitlesstcg.com" + url_tail
            card_id = self.read_card(url)

        self.save_list_to_file([set_code], "logs/scraped_pocket_set_list.txt")
        logger.info(f"Scraped {len(cards)} cards from set: {set_code}.")

        return card_id

    def scrape_existed_set(self, set_code):
        card_id = None
        # specifically for Promo sets, needs to change for the next era
        folder = "data_pocket/P-A/"
        existed_cards = {
            filename[:-5]
            for filename in os.listdir(folder)
            if filename.endswith(".json")
        }

        set_link = f"https://pocket.limitlesstcg.com/cards/{set_code}/"
        content = self.get_content(set_link)
        soup = bs4.BeautifulSoup(content, "html.parser")
        cards = [
            a["href"]
            for a in soup.find("div", class_="card-search-grid").find_all("a")
            if a["href"].split("P-A/")[1] not in existed_cards
        ]

        for url_tail in tqdm(cards, desc=f"Downloading {set_code}"):
            url = "https://pocket.limitlesstcg.com" + url_tail
            card_id = self.read_card(url)

        self.save_list_to_file([set_code], "logs/scraped_pocket_set_list.txt")
        logger.info(f"Scraped {len(cards)} cards from set: {set_code}.")

        return card_id

    def update(self):
        """
        Download the newest set.

        """
        logger.info("===== Updating started (pocket) =====")
        downloaded_sets = self.get_downloaded_set_list(lang="pocket")

        url = "https://pocket.limitlesstcg.com/cards"
        content = self.get_content(url)
        soup = bs4.BeautifulSoup(content, "html.parser")
        set_list = []
        for link in set(
            a["href"]
            for a in soup.find(
                "table", class_="data-table sets-table striped"
            ).find_all("a")
        ):
            set_list.append(link.split("cards/")[1])

        scraped = 0
        # need to update promo sets sometimes
        for s in set_list:
            if s not in downloaded_sets:
                last_id = self.scrape_set(s)
                self.upadte_readme(last_id, lang="pocket")
                downloaded_sets.add(s)
                scraped += 1
            elif s == "P-A":
                last_id = self.scrape_existed_set(s)
                self.upadte_readme(last_id, lang="pocket")
                scraped += 1
        logger.info(f"Searched {len(set_list)} sets; downloaded {scraped} sets.")
