"""
    Scrape Korean card info from pokemoncard.co.kr

    September 15, 2026 by Weihang
"""

import copy
import json
import re

from bs4 import Comment

import paths
from Card import Card
from CardScraper import CardScraper
from loguru import logger
from tqdm import tqdm

SITE = "https://pokemoncard.co.kr"
#: The card list is only reachable through the page's own request, which
#: answers with 30 cards and the cursor to ask for the next 30.
LIST_API = f"{SITE}/v2/ajax2_dev2"
PAGE_SIZE = 30

#: Energy names as the site writes them, mapped to the wording the rest of
#: this database already uses.
TYPES = {
    "풀": "Grass",
    "불꽃": "Fire",
    "물": "Water",
    "번개": "Lightning",
    "초": "Psychic",
    "격투": "Fighting",
    "악": "Dark",
    "강철": "Metal",
    "페어리": "Fairy",
    "드래곤": "Dragon",
    "무색": "Colorless",
    # An attack that costs nothing, written the way TCG Pocket writes it.
    "0코스트": "No Energy Cost",
}

#: The retreat icons carry no name, only the file the site draws them from.
TYPES_BY_FILE = {
    "type1": "Grass",
    "type2": "Fire",
    "type3": "Water",
    "type4": "Lightning",
    "type5": "Psychic",
    "type6": "Fighting",
    "type7": "Dark",
    "type8": "Metal",
    "type9": "Colorless",
    "type10": "Fairy",
    "type11": "Dragon",
}

#: Trainer rules repeat on every card of their kind, so they are not stored.
TRAINER_RULES = ("서포트 룰", "아이템 룰", "스타디움 룰", "포켓몬의 도구 룰", "포켓몬 도구 룰")

CARD_TYPES = {
    "아이템": "아이템",
    "서포트": "서포트",
    "스타디움": "스타디움",
    "포켓몬의 도구": "포켓몬의 도구",
    "기본 에너지": "기본 에너지",
    "특수 에너지": "특수 에너지",
}


class CardScraperKO(CardScraper):
    def __init__(self, delay=None):
        super().__init__(delay=delay)
        self.session.headers.update(
            {"X-Requested-With": "XMLHttpRequest", "Referer": f"{SITE}/cards"}
        )

    def get_url(self, card_num):
        return f"{SITE}/cards/detail/{card_num}"

    def energy_name(self, img):
        """English name of the energy an icon stands for."""
        title = (img.get("title") or "").strip()
        if title in TYPES:
            return TYPES[title]
        stem = img.get("src", "").split("/")[-1].split(".")[0]
        if stem in TYPES_BY_FILE:
            return TYPES_BY_FILE[stem]
        logger.warning(f"Unseen energy icon {title or stem!r}")
        return title or stem

    def read_text(self, tag):
        """Text of a block, with energy icons written out by name."""
        if tag is None:
            return ""
        clone = copy.copy(tag)
        for small in clone.find_all("small", class_="small_type_sm"):
            small.decompose()
        for img in clone.find_all("img"):
            img.replace_with(self.energy_name(img))
        return re.sub(r"\s+", " ", clone.get_text(" ", strip=True)).strip()

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    def get_header(self, card, soup):
        name = soup.select_one(".card-hp.title")
        card.set_card_name(name.get_text(strip=True) if name else "")
        logger.debug(f"name: {card.name}")

        level = soup.select_one(".card-hp.level")
        if level and level.get_text(strip=True):
            card.set_level(level.get_text(strip=True))
            logger.debug(f"level: {card.level}")

        hp = soup.find("span", class_="hp_num")
        if hp:
            digits = re.sub(r"\D", "", hp.get_text())
            if digits:
                card.set_hp(int(digits))
                logger.debug(f"hp: {card.hp}")
            holder = hp.find_parent("span", class_="card-hp")
            types = [self.energy_name(img) for img in holder.find_all("img")] if holder else []
            if types:
                card.set_types(types)
                logger.debug(f"types: {card.types}")

    def get_card_type(self, card, soup):
        info = soup.find("div", class_="pokemon-info")
        text = info.get_text(" ", strip=True).split(":", 1)[-1].strip() if info else ""
        if not text:
            card.set_card_type("Pokémon")
            return

        # A card can name a mechanic next to its kind, as in
        # "기본 포켓몬 | 메가진화 ex".
        parts = [part.strip() for part in text.split("|") if part.strip()]
        text = parts[0]
        for marker in parts[1:]:
            card.add_tag(marker)
            logger.debug(f"marker: {marker}")

        if text.endswith("포켓몬"):
            card.set_card_type("Pokémon")
            stage = text[: -len("포켓몬")].strip()
            if stage:
                card.set_stage(stage)
                logger.debug(f"stage: {card.stage}")
        else:
            card.set_card_type(CARD_TYPES.get(text, text))
        logger.debug(f"card type: {card.card_type}")

    def get_print_info(self, card, soup):
        info = soup.find("div", class_="pre_info_wrap")
        if not info:
            return
        symbols = info.find_all("img")
        if symbols:
            set_img = symbols[0]["src"]
            set_name = set_img.split("/")[-1].split(".")[0]
            card.set_set(set_name, set_img)
            logger.debug(f"set: {card.set_name}")
        if len(symbols) > 1:
            mark = symbols[1]["src"].split("/")[-1].split(".")[0]
            card.set_mark(mark)
            logger.debug(f"regulation: {card.regulation}")

        number_tag = info.find("span", class_="p_num")
        if number_tag:
            collector = "".join(number_tag.find_all(string=True, recursive=False)).strip()
            if "/" in collector:
                number, total = collector.split("/", 1)
            else:
                number, total = collector, -1
            card.set_collector(number.strip(), str(total).strip())
            logger.debug(f"number: {card.number} out of {card.set_total}")

            rarity = number_tag.find("span", id="no_wrap_by_admin")
            if rarity and rarity.get_text(strip=True):
                card.set_rarity(rarity.get_text(strip=True))
                logger.debug(f"rarity: {card.rarity}")

    def get_author(self, card, soup):
        info = soup.find("p", class_="illustrator")
        if info:
            author = [
                line.strip()
                for line in info.get_text("\n").split("\n")
                if line.strip() and line.strip() != "일러스트"
            ]
            if author:
                card.set_author(author)
                logger.debug(f"author: {card.author}")

    def get_abilities_and_attacks(self, card, soup):
        block = soup.find("div", class_="pokemon-abilities")
        if not block:
            return
        for skill in block.find_all("div", class_="ability"):
            label = skill.find("h4", class_="label")
            name_tag = skill.find("span", class_="skil_name")
            name = name_tag.get_text(strip=True) if name_tag else ""
            heading = label.get_text(" ", strip=True) if label else ""
            effect = self.read_text(skill.find("p"))

            if any(rule in heading for rule in TRAINER_RULES):
                continue

            area = skill.find("div", class_="area-parent")
            cost = [self.energy_name(img) for img in area.find_all("img")] if area else []
            damage_tag = skill.find("span", class_="plus")

            # A rule is written "[... 룰]" or ends in 룰, and never carries an
            # energy cost. An attack whose name merely contains those letters,
            # such as 마인드룰러, is an attack.
            is_rule = (
                not cost
                and damage_tag is None
                and bool(
                    re.search(r"\[[^\]]*룰\]", name)
                    or name.endswith("룰")
                    or heading.endswith("룰")
                )
            )
            if is_rule:
                if effect:
                    card.set_rule_box(effect)
                    logger.debug(f"rule box: {card.rule_box}")
                    logger.debug(f"tags: {card.tags}")
                continue
            if skill.find("span", id="skill_label"):
                card.add_ability(name, effect)
                logger.debug(f"ability [{name}]: {effect}")
                continue
            if not name:
                # A Trainer card writes its effect where attacks would be.
                card.set_effect(effect)
                logger.debug(f"effect: {card.effect}")
                continue

            damage = damage_tag.get_text(strip=True) if damage_tag else None
            card.add_attack(cost, name, damage, effect)
            logger.debug(f"attack [{name}]: {cost}: {damage}: {effect}")

    def get_stats(self, card, soup):
        block = soup.find("div", class_="pokemon-stats")
        if not block:
            return
        for stat in block.find_all("div", class_="stat"):
            heading = stat.find("h4")
            title = heading.get_text(strip=True) if heading else ""
            icons = [self.energy_name(img) for img in stat.find_all("img")]
            value_tag = stat.find("span")
            value = value_tag.get_text(strip=True) if value_tag else None
            if title == "약점":
                card.set_weakness(icons, value)
                logger.debug(f"weak: {card.weakness}")
            elif title == "저항력":
                card.set_resistance(icons, value)
                logger.debug(f"resist: {card.resistance}")
            elif title == "후퇴":
                card.set_retreat(len(icons))
                logger.debug(f"retreat: {card.retreat}")

    def get_set_and_dex(self, card, soup):
        link = soup.find("a", class_="search_href")
        if link:
            card.set_set_full_name(link.get_text(strip=True))
            logger.debug(f"set full name: {card.set_full_name}")

        for block in soup.find_all("div", class_="pokemon-detail"):
            dex = block.find("div", class_="col-md-4")
            if dex:
                # The site leaves the Pokédex number in an HTML comment on many
                # cards — "<!--No. 025-->" — and get_text() cannot see comments.
                comments = dex.find_all(string=lambda s: isinstance(s, Comment))
                text = " ".join([dex.get_text(" ", strip=True), *(c.strip() for c in comments)])
                number = re.search(r"No\.\s*(\d+)\s*([^\s키]*)", text)
                if number:
                    card.set_pokedex(int(number.group(1)), number.group(2).strip())
                    logger.debug(f"pokedex: {card.pokedex_number}, {card.pokemon_category}")
                size = re.search(r"키\s*:\s*(\S+\s*\S*?)\s*몸무게\s*:\s*(\S+\s*\S*)", text)
                if size:
                    card.set_ht_wt(size.group(1).strip(), size.group(2).strip())
                    logger.debug(f"height: {card.height}, weight: {card.weight}")
            flavor = block.find("div", class_="colsit")
            if flavor and flavor.find("p"):
                card.set_flavor_text(flavor.find("p").get_text(strip=True))
                logger.debug(f"flavor: {card.flavor_text}")

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    def read_card(self, card_num):
        card = Card()
        card.set_lang("ko")
        card.set_ko_id(card_num)
        card.set_url(self.get_url(card_num))
        logger.debug(f"url: {card.url}")

        soup = self.get_soup(card.url)
        if soup is None:
            logger.debug(f"Card {card_num} could not be fetched")
            return "Page not found"

        image = soup.find("img", class_="feature_image")
        if image is None:
            logger.debug(f"Card {card_num} not found!")
            return "Page not found"
        card.set_img(image["src"].split("?")[0])
        logger.debug(f"img: {card.img}")

        self.get_header(card, soup)
        self.get_card_type(card, soup)
        self.get_print_info(card, soup)
        self.get_author(card, soup)
        self.get_abilities_and_attacks(card, soup)
        self.get_stats(card, soup)
        self.get_set_and_dex(card, soup)

        card.save()
        del card
        return "Successfully scraped"

    # ------------------------------------------------------------------
    # Updating
    # ------------------------------------------------------------------

    def known_ids(self):
        """Card numbers already saved under `data_ko/`."""
        ids = set()
        for path in paths.data_dir("ko").rglob("*.json"):
            try:
                card = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if card.get("ko_id"):
                ids.add(str(card["ko_id"]))
        return ids

    def list_page(self, cursor):
        """One page of the card list, retried if the site stumbles.

        The next page is only reachable through the cursor this one returns,
        so a page that fails is retried rather than skipped.
        """
        payload = {
            "action": "search_text_cards",
            "search_text": "",
            "search_params": "all",
            "limit": str(cursor),
        }
        for attempt in range(1, self.retries + 1):
            self._wait_turn()
            try:
                response = self.session.post(
                    LIST_API,
                    files={key: (None, value) for key, value in payload.items()},
                    timeout=self.timeout,
                )
                return json.loads(response.text)
            except Exception as error:
                logger.warning(
                    f"Card list at cursor {cursor} failed ({error.__class__.__name__}), attempt {attempt}"
                )
                self._back_off(attempt)
        return None

    def list_site_ids(self):
        """Every card number the site lists, newest first."""
        ids = []
        cursor = 0
        while True:
            data = self.list_page(cursor)
            if data is None:
                logger.error(f"Card list unreadable at cursor {cursor}; stopping at {len(ids)} cards")
                break

            result = data.get("result") or {}
            entries = result.values() if isinstance(result, dict) else result
            found = [str(entry["CardNum"]) for entry in entries if entry.get("CardNum")]
            if not found:
                break
            ids += found
            cursor = data.get("limit")
            if cursor is None:
                break
            if len(ids) % (PAGE_SIZE * 50) == 0:
                logger.info(f"Listed {len(ids)} cards so far…")
        logger.info(f"Site lists {len(ids)} cards.")
        return ids

    def update(self, limit=None):
        """Download every card the site lists that is not on disk yet."""
        logger.info("===== Updating started (ko) =====")

        site_ids = self.list_site_ids()
        if not site_ids:
            logger.error("Could not list any card; aborting update.")
            return

        known = self.known_ids()
        seen = set()
        missing = []
        for card_num in site_ids:
            # The list can repeat a card across pages; fetch it once.
            if card_num not in known and card_num not in seen:
                seen.add(card_num)
                missing.append(card_num)
        logger.info(
            f"{len(set(site_ids))} cards listed, {len(known)} already stored, {len(missing)} to download."
        )
        if limit:
            missing = missing[:limit]

        scraped_list, error_list = [], []
        for card_num in tqdm(missing, desc="Downloading ko", disable=None):
            code = self.read_card_safely(card_num, default="Something wrong")
            if code == "Successfully scraped":
                scraped_list.append(card_num)
            else:
                error_list.append(card_num)

        self.save_list_to_file(scraped_list, "scraped_ko_id_list.txt")
        self.save_list_to_file(error_list, "error_ko_id_list.txt")
        if scraped_list:
            self.update_readme(scraped_list[0], lang="ko")
        logger.info(f"Downloaded {len(scraped_list)} cards; {len(error_list)} had no page.")
