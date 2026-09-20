"""
    Scrape English card info from pkmncards.com

    May 29, 2024 by Weihang
"""

import json
import re

import bs4
import paths
from Card import Card
from CardScraper import CardScraper
from loguru import logger
from tqdm import tqdm

SETS_URL = "https://pkmncards.com/sets/"


class CardScraperEN(CardScraper):
    #: This site answers a burst with 403, so it gets a slower cadence.
    delay = 1.5
    #: It also serves a proof-of-work page to newer user agents.
    user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"

    def get_img_url(self, card, soup):
        img = soup.find("img", class_="card-image")["src"]
        card.set_img(img)
        logger.debug(f"img: {card.img}")

    def clean_name(self, text):
        return text.replace("-GX", " GX").replace("-EX", " EX")

    def get_name(self, card, page):
        name = page.find("span", class_="name").get_text()
        card.set_card_name(self.clean_name(name))
        logger.debug(f"name: {card.name}")

    def get_hp(self, card, page):
        hp_info = page.find("span", class_="hp")
        if hp_info:
            hp = int(hp_info.get_text().split()[0])
            card.set_hp(hp)
            logger.debug(f"hp: {card.hp}")

    def get_types(self, card, page):
        types_info = page.find("span", class_="color")
        if types_info:
            types = [abbr["title"] for abbr in types_info.find_all("abbr")]
            card.set_types(types)
            logger.debug(f"types: {card.types}")

    def get_card_type(self, card, page):
        card_type_info = page.find("span", class_="type")
        if card_type_info:
            subtype_info = page.find("span", class_="sub-type")
            if subtype_info:
                card_type_info = subtype_info
            card_type = card_type_info.get_text().strip()
            card.set_card_type(card_type)
            logger.debug(f"card type: {card.card_type}")

    def get_stage(self, card, page):
        stage_info = page.find("span", class_="stage")
        if stage_info:
            stage = stage_info.get_text().strip()
            card.set_stage(stage)
            logger.debug(f"stage: {card.stage}")

    def get_evolve_from(self, card, page):
        evolve_from_info = page.find("span", class_="evolves")
        if evolve_from_info:
            text = evolve_from_info.get_text().strip()
            if " and " in text:
                match = re.search(r"Evolves from ([\w\W]+) and", text)
                if match:
                    card.set_evolve_from(self.clean_name(match.group(1)))
                    logger.debug(f"evolve from: {card.evolve_from}")
            else:
                match = re.search(r"Evolves from ([\w\W]+)", text)
                if match:
                    card.set_evolve_from(self.clean_name(match.group(1)))
                    logger.debug(f"evolve from: {card.evolve_from}")

    def get_ability(self, card, text):
        row1, row2 = text.split("\n")
        ability_name = row1.split("⇢ ")[1]
        ability_effect = row2
        card.add_ability(ability_name, ability_effect)
        logger.debug(
            f"ability [{card.abilities[-1]["name"]}]: {card.abilities[-1]["effect"]}"
        )

    def get_poke_power(self, card, text):
        row1, row2 = text.split("\n")
        poke_power_name = row1.split("⇢ ")[1]
        poke_power_effect = row2
        card.set_poke_power(poke_power_name, poke_power_effect)
        logger.debug(
            f"poke power [{card.poke_power["name"]}]: {card.poke_power["effect"]}"
        )

    def get_poke_body(self, card, text):
        row1, row2 = text.split("\n")
        poke_body_name = row1.split("⇢ ")[1]
        poke_body_effect = row2
        card.set_poke_body(poke_body_name, poke_body_effect)
        logger.debug(
            f"poke body [{card.poke_body["name"]}]: {card.poke_body["effect"]}"
        )

    def get_ancient_trait(self, card, text):
        row1, row2 = text.split("\n")
        trait_name = row1.split("⇢ ")[1]
        trait_effect = row2
        card.set_ancient_trait(trait_name, trait_effect)
        logger.debug(
            f"ancient trait [{card.ancient_trait["name"]}]: {card.ancient_trait["effect"]}"
        )

    def get_held_item(self, card, text):
        row1, row2 = text.split("\n")
        item = row1.split("⇢ ")[1]
        item_effect = row2
        card.set_held_item(item, item_effect)
        logger.debug(
            f"held item [{card.held_item["item"]}]: {card.held_item["effect"]}"
        )

    def get_attack(self, card, p_tag):
        first_span = p_tag.find("abbr").find_next_sibling("span")
        attack_cost = [
            abbr["title"] for abbr in first_span.find_previous_siblings("abbr")
        ][::-1]
        p_tag_content = p_tag.get_text().strip()
        if "\n" in p_tag_content:
            row1, row2 = p_tag_content.split("\n")
        else:
            row1 = p_tag_content
            row2 = None
        if "{+}" in row1:
            attack_cost.append("+")
        if ":" in row1:
            attack_damage = self.read_attack_damage(row1.split(": ")[1])
        else:
            attack_damage = None
        attack_name = row1.split("→ ")[1].split(" :")[0].strip().replace("-GX", " GX")
        attack_effect = row2
        card.add_attack(attack_cost, attack_name, attack_damage, attack_effect)
        logger.debug(
            f"attack [{card.attacks[-1]["name"]}]: {card.attacks[-1]["cost"]}: {card.attacks[-1]["damage"]}: {card.attacks[-1]["effect"]}"
        )

    def get_vstar_power(self, card, p_tag, tool=False):
        if p_tag.find("a") and p_tag.find("a").get_text() == "Ability":
            if tool:
                row1, row2 = p_tag.get_text().split("\n")
            else:
                row0, row1, row2 = p_tag.get_text().split("\n")
            vstar_name = row1.split("⇢ ")[1]
            vstar_effect = row2
            card.set_vstar_power_ability(vstar_name, vstar_effect)
        else:
            vstar_cost = [abbr["title"] for abbr in p_tag.find_all("abbr")]
            content = p_tag.get_text().strip().split("\n")
            if tool:
                row1, row2 = content
            elif len(content) == 3:
                row0, row1, row2 = content
            else:
                row0, row1 = p_tag.get_text().strip().split("\n")
                row2 = None
            if ":" in row1:
                vstar_damage = self.read_attack_damage(row1.split(": ")[1])
            else:
                vstar_damage = None
            vstar_name = row1.split("→ ")[1].split(" :")[0].strip()
            vstar_effect = row2
            card.set_vstar_power_attack(
                vstar_cost, vstar_name, vstar_damage, vstar_effect
            )
        logger.debug(f"VSTAR power: {card.vstar_power}")

    def get_abilities_and_attacks(self, card, page):
        effect_text = ""
        nextVSTAR = False
        for p_tag in page.find("div", class_="text").find_all("p"):
            if p_tag.get_text().split("\n")[0] == "VSTAR Power" or nextVSTAR:
                if card.card_type == "Pokémon":
                    self.get_vstar_power(card, p_tag)
                elif card.card_type == "Pokémon Tool":
                    if nextVSTAR:
                        self.get_vstar_power(card, p_tag, tool=True)
                        nextVSTAR = False
                    else:
                        card.set_effect(p_tag.get_text().split("\n")[1].strip())
                        nextVSTAR = True
            elif p_tag.find("a"):
                category = p_tag.find("a").get_text()
                if category in ["Ability", "Pokémon Power"]:
                    self.get_ability(card, p_tag.get_text())
                elif category == "Poké-POWER":
                    self.get_poke_power(card, p_tag.get_text())
                elif category == "Poké-BODY":
                    self.get_poke_body(card, p_tag.get_text())
                elif category == "Ancient Trait":
                    self.get_ancient_trait(card, p_tag.get_text())
                elif category == "Held Item":
                    self.get_held_item(card, p_tag.get_text())
                else:
                    logger.error(f"Card {card.en_id} has unseen text: {category}!")
            elif "→" in p_tag.get_text():
                self.get_attack(card, p_tag)
            else:
                effect_text += "\n" + p_tag.get_text()
                card.set_effect(effect_text.strip())
                logger.debug(f"effect: {card.effect}")

    def get_weakness(self, card, page):
        weak_info = page.find("span", class_="weak")
        if weak_info:
            if weak_info.find("a").get_text().strip() != "n/a":
                weak_types = [abbr["title"] for abbr in weak_info.find_all("abbr")]
                weak_value = (
                    weak_info.find("span", title="Weakness Modifier").get_text().strip()
                )
            else:
                weak_types = []
                weak_value = None
            card.set_weakness(weak_types, weak_value)
            logger.debug(f"weak: {card.weakness}")

    def get_resistance(self, card, page):
        resist_info = page.find("span", class_="resist")
        if resist_info:
            if resist_info.find("a").get_text().strip() != "n/a":
                resist_types = [abbr["title"] for abbr in resist_info.find_all("abbr")]
                resist_value = (
                    resist_info.find("span", title="Resistance Modifier")
                    .get_text()
                    .strip()
                )
            else:
                resist_types = []
                resist_value = None
            card.set_resistance(resist_types, resist_value)
            logger.debug(f"resist: {card.resistance}")

    def get_retreat(self, card, page):
        retreat_info = page.find("span", class_="retreat")
        if retreat_info:
            card.set_retreat(int(retreat_info.find("abbr").get_text()))
            logger.debug(f"retreat: {card.retreat}")

    def get_author(self, card, page):
        author_info = page.find("div", class_="illus minor-text")
        if author_info:
            author = [
                span.find("a").get_text()
                for span in author_info.find_all("span", title="Illustrator")
            ]
            if author != ["n/a"]:
                card.set_author(author)
                logger.debug(f"author: {card.author}")
            level_info = author_info.find("span", class_="level")
            if level_info:
                level = level_info.get_text().split("LV.")[1]
                card.set_level(level)
                logger.debug(f"level: {card.level}")

    def get_release(self, card, page):
        info = page.find("div", class_="release-meta minor-text")
        series_info = info.find("span", title="Series")
        series = series_info.find("a").get_text() if series_info else None
        set_name = info.find("span", title="Set").find("a").get_text()
        code_info = info.find("span", title="Set Series Code")
        set_code = code_info.get_text() if code_info else None
        abbr_info = info.find("span", title="Set Abbreviation")
        set_abbr = abbr_info.get_text() if abbr_info else set_code
        if set_code == None and set_abbr == None:
            set_code = set_abbr = set_name
        elif set_code == None:
            set_code = set_abbr
        date = info.find("span", class_="date").get_text().strip("↘ ")
        card.set_set(set_abbr)
        logger.debug(f"set: {card.set_name}")
        card.set_set_extra(series, set_name, set_code, date)
        logger.debug(
            f"set extra: {card.series}, {card.set_full_name}, {card.set_code}, {card.date}"
        )

        number = info.find("span", class_="number").find("a").get_text()
        total_info = info.find("span", class_="out-of")
        if total_info:
            total = total_info.get_text().strip("/")
        else:
            total = None
        card.set_collector(number, total)
        logger.debug(f"number: {card.number} out of {card.set_total}")
        # Hyphenated like every other language, so "SVI" + "001" does not read
        # as one run-together word wherever this id is shown.
        card.set_out_id(f"{card.set_name}-{card.number}")

        rarity = info.find("span", class_="rarity").find("a").get_text()
        card.set_rarity(rarity)
        logger.debug(f"rarity: {card.rarity}")

    def get_reg_mark(self, card, page):
        reg_info = page.find("span", class_="Regulation Mark")
        if reg_info:
            mark = reg_info.find("a").get_text()
            card.set_mark(mark)
            logger.debug(f"regulation: {card.regulation}")

    def get_flavor_text(self, card, page):
        flavor_info = page.find("div", class_="flavor minor-text")
        if flavor_info:
            card.set_flavor_text(flavor_info.get_text())
            logger.debug(f"flavor: {card.flavor_text}")

    def get_rule(self, card, page):
        rule_info = page.find("div", class_="rules minor-text")
        if rule_info:
            rule_box = ""
            ignore_rule = [
                "Supporter rule",
                "Item rule",
                "Stadium rule",
                "Pokémon Tool rule",
            ]
            for rule in rule_info.find_all("div"):
                rule_text = rule.get_text()
                if "Tera Pokémon ex rule" in rule_text:
                    card.set_tera(lang="en")
                    continue
                if any(ig in rule_text for ig in ignore_rule):
                    continue
                text = rule_text.lstrip("·").strip()
                mega = re.match(r"The Mega-Evolved form of (.+)", text)
                if mega:
                    card.set_mega_evolves_from(mega.group(1).strip())
                    logger.debug(f"mega evolves from: {card.mega_evolves_from}")
                    continue
                # Named rules read "<name>: <rule>"; newer lines can omit the name.
                rule_box += "\n" + (text.split(": ", 1)[1] if ": " in text else text)
            rule_box = rule_box.strip()
            if rule_box:
                card.set_rule_box(rule_box.strip().replace("{*}", "Prism Star"))
                logger.debug(f"rule box: {card.rule_box}")
        logger.debug(f"tags: {card.tags}")

    def read_card(self, url):
        card = Card()

        card.set_url(url)
        logger.debug(f"url: {card.url}")

        content = self.get_content(card.url)
        soup = bs4.BeautifulSoup(content, "html.parser")

        self.get_img_url(card, soup)

        card_page = soup.find("div", class_="tab text")

        self.get_name(card, card_page)
        self.get_hp(card, card_page)
        self.get_types(card, card_page)
        self.get_card_type(card, card_page)
        if card.card_type != "Basic Energy":
            self.get_stage(card, card_page)
            self.get_evolve_from(card, card_page)
            self.get_abilities_and_attacks(card, card_page)
            self.get_weakness(card, card_page)
            self.get_resistance(card, card_page)
            self.get_retreat(card, card_page)
        self.get_author(card, card_page)
        self.get_release(card, card_page)
        self.get_reg_mark(card, card_page)
        self.get_flavor_text(card, card_page)
        self.get_rule(card, card_page)

        card_id = card.out_id

        card.save()
        del card
        return card_id

    def stored_card_urls(self):
        """Every card url already saved under `data_en/`.

        Matching on the url rather than on a set-specific file-name rule lets
        one code path skip what is already stored, in every set.
        """
        urls = set()
        for path in paths.data_dir("en").rglob("*.json"):
            try:
                urls.add(json.loads(path.read_text(encoding="utf-8")).get("url"))
            except (ValueError, OSError):
                logger.warning(f"Could not read {path}")
        urls.discard(None)
        return urls

    def set_card_links(self, set_name):
        """Every card url listed in one set."""
        soup = self.get_soup(f"https://pkmncards.com/set/{set_name}/")
        if soup is None:
            logger.error(f"Could not open set {set_name}")
            return []
        main = soup.find("main", class_="content")
        if main is None:
            logger.error(f"Set {set_name} has no card list")
            return []
        return [a["href"] for a in main.find_all("a") if "/card/" in a.get("href", "")]

    def scrape_set(self, set_name, skip_urls=frozenset()):
        """Download the cards of one set that are not stored yet.

        Returns the last card id written and how many cards the set listed.
        A set that lists nothing was unreachable, never empty.
        """
        cards = self.set_card_links(set_name)
        new_cards = [url for url in cards if url not in skip_urls]

        card_id = None
        for url in tqdm(new_cards, desc=f"Downloading {set_name}", leave=False, disable=None):
            card_id = self.read_card_safely(url) or card_id

        if cards:
            self.save_list_to_file([set_name], "scraped_en_set_list.txt")

        # How many of the set's cards were already on disk. Without it, "120
        # listed, 0 downloaded" reads the same whether all 120 are stored or
        # none are, which is how a whole set — 30th Celebration — sat missing
        # without a single line saying so.
        held = len(cards) - len(new_cards)
        logger.info(f"Set {set_name}: {len(cards)} cards listed, {held} stored, {len(new_cards)} downloaded.")
        if cards and held == 0 and card_id is None:
            logger.error(f"Set {set_name} lists {len(cards)} cards and none of them is stored")
        return card_id, len(cards)

    def list_sets(self):
        """Every set the site publishes."""
        soup = self.get_soup(SETS_URL)
        if soup is None:
            logger.error("Could not open the set index")
            return []
        content = soup.find("div", class_="entry-content")
        if content is None:
            logger.error("Set index has no content block")
            return []
        set_list = []
        for a in content.find_all("a"):
            link = a.get("href", "")
            if "/set/" in link and "collection/shiny-vault" not in link:
                name = link.split("/set/")[1].strip("/")
                if name and name not in set_list:
                    set_list.append(name)
        return set_list

    def update(self, limit=None):
        """Download every card that is listed but not stored yet.

        Every set is re-checked, because promo sets keep growing after their
        first release; cards already on disk are skipped by url.
        """
        logger.info("===== Updating started (en) =====")
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
        for set_name in tqdm(set_list, desc="Checking en sets", disable=None):
            card_id, listed = self.scrape_set(set_name, skip_urls=stored)
            last_id = card_id or last_id
            if not listed:
                failed.append(set_name)

        # A set that would not list is usually a moment of throttling, so it
        # is worth one more pass before the run gives up on it.
        if failed:
            logger.warning(f"Retrying {len(failed)} sets that did not list: {failed}")
            for set_name in failed:
                card_id, listed = self.scrape_set(set_name, skip_urls=stored)
                last_id = card_id or last_id
                if not listed:
                    logger.error(f"Set {set_name} is still unreachable")

        if last_id:
            self.update_readme(last_id, lang="en")
        logger.info(f"Checked {len(set_list)} sets.")
