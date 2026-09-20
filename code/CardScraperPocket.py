"""
    Scrape TCG Pocket card info from limitlesstcg.com

    Februray 18, 2025 by Weihang
"""

import json
import re

import paths
from Card import Card
from CardScraper import CardScraper
from loguru import logger
from tqdm import tqdm

SITE = "https://pocket.limitlesstcg.com"


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

    def __init__(self, delay=None):
        super().__init__(delay=delay)
        #: set url -> (release date, number of cards), so one lookup per set
        self._releases = {}

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
        """Card text with energy letters written out and spacing tidied."""

        def energy(match):
            letter = match.group(1)
            if letter in self.letter_to_type and letter not in {"0", "+"}:
                return f" {{{self.letter_to_type[letter]}}} "
            return match.group(0)

        text = re.sub(r"\[([A-Z0-9+])\]", energy, text)
        text = re.sub(r"\.(\S)", r". \1", text)
        return re.sub(r"\s+", " ", text).strip()

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
        # Joined with a space: the page puts part of the sentence in its own
        # element, and stripping without a separator glues the words together.
        effect_text = self.read_effect(
            page.find_all("div", class_="card-text-section")[1].get_text(" ", strip=True)
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
                    " ", strip=True
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
                    " ", strip=True
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

    def get_set_release(self, set_url):
        """Release date and card count of a set, read once per set."""
        if set_url in self._releases:
            return self._releases[set_url]

        date, set_total = None, None
        soup = self.get_soup(set_url)
        line = soup.find("div", class_="infobox-line") if soup else None
        if line:
            release_info = line.get_text().strip().split("•")
            if len(release_info) > 1:
                date = release_info[0].strip()
                set_total = int(release_info[1].strip().split()[0])
        self._releases[set_url] = (date, set_total)
        return date, set_total

    def get_set_info(self, card, page):
        set_name = page.find("span", class_="text-lg").get_text().split("(")[0].strip()
        set_code = page.find("img")["alt"]
        set_img_url = page.find("img")["src"]
        card.set_set(set_name, set_img_url)
        card.set_set_code(set_code)
        logger.debug(f"set name: {card.set_name}")
        logger.debug(f"set code: {card.set_code}")
        logger.debug(f"set img: {card.set_img}")

        set_url = SITE + page.find("a")["href"]
        date, set_total = self.get_set_release(set_url)
        if date:
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
            if clean_info in self.img_to_rarity:
                rarity = self.img_to_rarity[clean_info]
            elif set(clean_info) <= set("◊☆✵♦") and clean_info:
                # An unseen symbol is still a rarity: keep it rather than
                # mistaking it for a pack name.
                rarity = clean_info
                logger.warning(f"Unseen rarity symbol {clean_info!r} on {card.url}")
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

        soup = self.get_soup(card.url)
        if soup is None:
            logger.error(f"Could not fetch {url}")
            return None

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

    def stored_card_urls(self):
        """Every card url already saved under `data_pocket/`."""
        urls = set()
        for path in paths.data_dir("pocket").rglob("*.json"):
            try:
                urls.add(json.loads(path.read_text(encoding="utf-8")).get("url"))
            except (ValueError, OSError):
                logger.warning(f"Could not read {path}")
        urls.discard(None)
        return urls

    def set_card_links(self, set_code):
        """Every card url listed in one set."""
        soup = self.get_soup(f"{SITE}/cards/{set_code}/")
        if soup is None:
            logger.error(f"Could not open set {set_code}")
            return []
        grid = soup.find("div", class_="card-search-grid")
        if grid is None:
            logger.error(f"Set {set_code} has no card grid")
            return []
        return [SITE + a["href"] for a in grid.find_all("a") if a.get("href")]

    def scrape_set(self, set_code, skip_urls=frozenset()):
        """Download the cards of one set that are not stored yet.

        Returns the last card id written and how many cards the set listed.
        A set that lists nothing was unreachable, never empty.
        """
        cards = self.set_card_links(set_code)
        new_cards = [url for url in cards if url not in skip_urls]

        card_id = None
        for url in tqdm(new_cards, desc=f"Downloading {set_code}", leave=False, disable=None):
            card_id = self.read_card_safely(url) or card_id

        if cards:
            self.save_list_to_file([set_code], "scraped_pocket_set_list.txt")
        # How many were already on disk: "120 listed, 0 downloaded" otherwise
        # reads the same whether every card is stored or none is.
        held = len(cards) - len(new_cards)
        logger.info(f"Set {set_code}: {len(cards)} cards listed, {held} stored, {len(new_cards)} downloaded.")
        if cards and held == 0 and card_id is None:
            logger.error(f"Set {set_code} lists {len(cards)} cards and none of them is stored")
        return card_id, len(cards)

    def list_sets(self):
        """Every set the site publishes, oldest first."""
        soup = self.get_soup(f"{SITE}/cards")
        if soup is None:
            logger.error("Could not open the set index")
            return []
        table = soup.find("table", class_="data-table sets-table striped")
        if table is None:
            logger.error("Set index has no set table")
            return []
        set_list = []
        for a in table.find_all("a"):
            code = a.get("href", "").split("cards/")[-1]
            if code and code not in set_list:
                set_list.append(code)
        return set_list

    def update(self, limit=None):
        """Download every card that is listed but not stored yet.

        Every set is re-checked, because promo sets keep growing after their
        first release; cards already on disk are skipped by url.
        """
        logger.info("===== Updating started (pocket) =====")
        set_list = self.list_sets()
        if not set_list:
            logger.error("Could not list any set; aborting update.")
            return
        logger.info(f"Site lists {len(set_list)} sets.")

        stored = self.stored_card_urls()
        logger.info(f"{len(stored)} cards already stored.")
        if limit:
            set_list = set_list[:limit]

        last_id, failed = None, []
        for set_code in tqdm(set_list, desc="Checking pocket sets", disable=None):
            card_id, listed = self.scrape_set(set_code, skip_urls=stored)
            last_id = card_id or last_id
            if not listed:
                failed.append(set_code)

        # A set that would not list is usually a moment of throttling, so it
        # is worth one more pass before the run gives up on it.
        if failed:
            logger.warning(f"Retrying {len(failed)} sets that did not list: {failed}")
            for set_code in failed:
                card_id, listed = self.scrape_set(set_code, skip_urls=stored)
                last_id = card_id or last_id
                if not listed:
                    logger.error(f"Set {set_code} is still unreachable")

        if last_id:
            self.update_readme(last_id, lang="pocket")
        logger.info(f"Checked {len(set_list)} sets.")
