"""
    Scrape card info from the Pokémon Asia websites

    One site serves several locales from the same layout and the same card
    ids, so one scraper covers Traditional Chinese and its sibling regions.

    Februray 25, 2025 by Weihang
"""

import re

import paths
from Card import Card
from CardScraper import CardScraper
from loguru import logger
from tqdm import tqdm

#: Locale code on asia.pokemon-card.com -> folder suffix used under `data_`.
LOCALES = {
    "tw": "tc",  # Traditional Chinese (Taiwan)
    "hk": "hk",  # Traditional Chinese (Hong Kong)
    "th": "th",  # Thai
    "id": "id",  # Indonesian
    "sg": "sg",  # English (Singapore)
    "my": "my",  # English (Malaysia)
    "ph": "ph",  # English (Philippines)
}

#: Cards are listed 20 to a page.
PAGE_SIZE = 20

#: A promo symbol carries no set code, so the product name has to name the set.
PROMO_SETS = {
    "特典卡 朱&紫": "SV-P",
    "特典卡 劍&盾": "S-P",
    "特典卡 超級進化": "M-P",
}


class CardScraperTC(CardScraper):
    def __init__(self, locale="tw", delay=None):
        super().__init__(delay=delay)
        if locale not in LOCALES:
            raise ValueError(f"Unknown locale {locale!r}; expected one of {sorted(LOCALES)}")
        self.locale = locale
        self.lang = LOCALES[locale]
        self._expansion_codes = None

    def get_url(self, card_id):
        return f"https://asia.pokemon-card.com/{self.locale}/card-search/detail/{card_id}/"

    def get_list_url(self, page):
        return f"https://asia.pokemon-card.com/{self.locale}/card-search/list/?pageNo={page}"

    def extract_energy(self, url):
        """
        Get the Energy from the energy image url

        """
        return url.split(".png")[0].split("/")[-1]

    def format_set_name(self, s):
        """Turn a set-symbol file name into the set code it stands for.

        The symbol file names are inconsistent across eras, carrying image
        suffixes (`@4x`), locale prefixes (`twhk_`), stray spaces and even
        Japanese words, so everything that is not the code is stripped here.
        """
        name = str(s)
        name = name.split("/")[-1].split("?")[0]
        for suffix in (".png", ".jpg", ".gif", ".webp"):
            if name.lower().endswith(suffix):
                name = name[: -len(suffix)]
        name = re.sub(r"@\d*x", "", name)
        name = re.sub(r"[^\x00-\x7F]+", "", name)  # drop エキスパンションマーク & co.
        for affix in (
            "exp_twhk_",
            "twhk_exp_",
            "mark_expantion_",
            "expansion_mark_",
            "expantion_",
            "twhk_",
            "exp_",
        ):
            name = name.replace(affix, "")
        name = re.sub(r"^(tw|hk|th|id|sg|my|ph)_", "", name, flags=re.IGNORECASE)
        name = re.sub(r"^S_(?=S)", "", name)  # S_S5R_F_OL -> S5R_F_OL
        name = re.sub(r"(_F)?(_OL)?$", "", name)  # S5R_F_OL -> S5R
        name = re.sub(r"[_\-]?(exp|expansion|out)$", "", name, flags=re.IGNORECASE)
        name = name.strip(" _-")
        if not name:
            return str(s)

        # Keep a spelling already used on disk, so a clean name never churns.
        # Compared by name rather than by path, because a case-insensitive
        # file system would otherwise accept `svf` for the folder `SVF`.
        folder = paths.data_dir(self.lang)
        if folder.is_dir() and name in {entry.name for entry in folder.iterdir()}:
            return name
        official = self.canonical_set_code(name)
        if official:
            return official
        if len(name) >= 3 and not name[1].isdigit():
            name = name[:2].upper() + name[2:]
        return name

    def parse_collector(self, collector):
        """Split "108/086" into the card number and the set total.

        A card printed with two numbers reads "151/103,152/103", where the
        first pair names it. A card with no numbered slot reads "n/a" and is
        kept exactly as printed rather than split into nonsense.
        """
        parts = collector.split(" ")[0].split(",")[0].split("/")
        if len(parts) == 2 and any(char.isdigit() for char in parts[1]):
            return parts[0], parts[1]
        # Some promos print the set code where the total belongs — "039/M-P".
        # The first half still names the card, and keeping the pair whole would
        # put a separator in the card's own file name.
        if len(parts) == 2 and any(char.isdigit() for char in parts[0]):
            return parts[0], -1
        if len(parts) == 1:
            return parts[0], -1
        logger.debug(f"collector number kept as printed: {collector!r}")
        return collector, -1

    def expansion_codes(self):
        """The set codes the site itself publishes, longest first."""
        if self._expansion_codes is None:
            codes = set()
            soup = self.get_soup(self.get_list_url(1))
            modal = soup.find("section", id="productSelectorModal") if soup else None
            if modal:
                for tag in modal.find_all("input"):
                    value = tag.get("value", "")
                    if value and not value.isdigit():
                        codes.add(value)
            self._expansion_codes = sorted(codes, key=len, reverse=True)
            logger.info(f"Loaded {len(self._expansion_codes)} expansion codes")
        return self._expansion_codes

    def canonical_set_code(self, name):
        """Match a cleaned symbol name to an official set code."""
        lowered = name.lower()
        for code in self.expansion_codes():
            if lowered == code.lower():
                return code
        for code in self.expansion_codes():
            if lowered.startswith(code.lower()):
                return code
        return None

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

            # The site closes most cards with an empty skill block, and files a
            # trainer rule in an unnamed one. A block with no name, no cost and
            # no damage is never an attack: its text is a rule, or nothing.
            if not name:
                cost_tag = skill.find("span", class_="skillCost")
                damage_tag = skill.find("span", class_="skillDamage")
                has_cost = bool(cost_tag and (cost_tag.find_all("img") or cost_tag.get_text(strip=True)))
                has_damage = bool(damage_tag and damage_tag.get_text(strip=True))
                if not has_cost and not has_damage:
                    stored = {getattr(card, "effect", None), getattr(card, "rule_box", None)}
                    if skill_effect and skill_effect not in stored:
                        if getattr(card, "rule_box", None):
                            logger.info(f"Unnamed block holds a second rule: {skill_effect[:60]}")
                        else:
                            card.set_rule_box(skill_effect)
                            logger.debug(f"rule box from an unnamed block: {card.rule_box}")
                    continue

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
            number, total = self.parse_collector(collector)
            card.set_collector(number, total)
            logger.debug(f"number: {card.number} out of {card.set_total}")

            set_img = focus.find("span", class_="expansionSymbol").find("img")["src"]
            set_name = set_img.split("mark/")[-1]
            if "PROMO" in set_name:
                # A promo symbol carries no code; the number does.
                set_name = card.number.split("/")[0] if "/" in str(card.number) else "PROMO"
                # A few promo pages state the printed "039/039" as the total. That
                # is a number, not a set code, and using it as one both misfiles
                # the card and puts a separator in its folder name, so it is left
                # to the promo lookup below instead.
                if str(card.set_total) not in ("-1", "None") and "/" not in str(card.set_total):
                    set_name = str(card.set_total)
            card.set_set(self.format_set_name(set_name), set_img)
            logger.debug(f"set: {card.set_name}, {card.set_img}")

            mark = focus.find("span", class_="alpha").get_text(strip=True)
            card.set_mark(mark)
            logger.debug(f"regulation: {card.regulation}")

            card.set_out_id(card.set_name + "-" + str(card.number))

        expansion = page.find("section", class_="expansionLinkColumn")
        if expansion:
            set_full_name = expansion.find("a").get_text(strip=True)
            card.set_set_full_name(set_full_name)
            logger.debug(f"set full name: {card.set_full_name}")
            if card.set_name == "PROMO" and set_full_name in PROMO_SETS:
                card.set_set(PROMO_SETS[set_full_name], card.set_img)
                card.set_out_id(card.set_name + "-" + str(card.number))
                logger.debug(f"promo set resolved to {card.set_name}")

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
            if size and size.find("span"):
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
        card.set_lang(self.lang)

        card.set_url(self.get_url(web_id))
        logger.debug(f"url: {card.url}")

        soup = self.get_soup(card.url)
        if soup is None:
            logger.error(f"Card id {web_id} could not be fetched")
            return "Page not found"

        card_page = soup.find("div", class_="wrapper")
        header = card_page.find("h1", class_="pageHeader") if card_page else None
        if header is None or header.get_text(strip=True) == "卡牌搜尋結果":
            logger.debug(f"Card id {web_id} not found!")
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

    # ------------------------------------------------------------------
    # Updating
    # ------------------------------------------------------------------

    def known_ids(self):
        """Card ids already saved for this locale, read from the stored urls."""
        ids = set()
        for path in paths.data_dir(self.lang).glob("*/*.json"):
            match = re.search(r"/detail/(\d+)", path.read_text(encoding="utf-8")[:300])
            if match:
                ids.add(int(match.group(1)))
        return ids

    def list_site_ids(self):
        """Every card id the site lists, newest first.

        The ids are not consecutive — whole blocks are unused — so the card
        list is walked instead of guessing the next id, which used to stop
        dead at the first gap wider than the look-ahead.
        """
        ids = []
        failed = []
        page = 1
        total_pages = None
        while total_pages is None or page <= total_pages:
            soup = self.get_soup(self.get_list_url(page))
            if soup is None:
                if total_pages is None:
                    logger.error("Could not open the card list at all")
                    break
                # One unreadable page must not hide the pages behind it.
                logger.error(f"Card list page {page} unavailable; carrying on")
                failed.append(page)
                page += 1
                continue
            if total_pages is None:
                total = soup.find("p", class_="resultNumber")
                count = int(total.get_text(strip=True)) if total else 0
                total_pages = max(1, -(-count // PAGE_SIZE))
                logger.info(f"Site lists {count} cards over {total_pages} pages ({self.locale}).")
            found = [
                int(match)
                for match in re.findall(
                    rf"/{self.locale}/card-search/detail/(\d+)/", str(soup)
                )
            ]
            if not found:
                logger.warning(f"Card list page {page} held no card")
            ids += found
            page += 1
        if failed:
            logger.warning(f"{len(failed)} list pages could not be read: {failed[:10]}")
        return ids

    def update(self, limit=None):
        """Download every card the site lists that is not on disk yet."""
        logger.info(f"===== Updating started ({self.lang}) =====")

        site_ids = set(self.list_site_ids())
        if not site_ids:
            logger.error("Could not list any card; aborting update.")
            return

        known = self.known_ids()
        if self.lang == "tc":
            known |= self.get_downloaded_id_list(lang="tc")
        missing = sorted(site_ids - known)
        logger.info(f"{len(site_ids)} cards listed, {len(known)} already stored, {len(missing)} to download.")
        if limit:
            missing = missing[:limit]

        scraped_list, question_list, missing_list = [], [], []
        for card_id in tqdm(missing, desc=f"Downloading {self.lang}", disable=None):
            code = self.read_card_safely(card_id, default="Something wrong")
            if code == "Successfully scraped":
                scraped_list.append(card_id)
            elif code == "Something wrong":
                # The card was not written: something in its page or its saving
                # failed. Recording it as scraped would hide it from every later
                # run, so it is only ever queried, and the next run tries again.
                question_list.append(card_id)
            elif code == "Page not found":
                missing_list.append(card_id)
            else:
                logger.error(f"Card {card_id} has unseen result code: {code}")

        self.save_list_to_file(scraped_list, f"scraped_{self.lang}_id_list.txt")
        self.save_list_to_file(question_list, f"question_{self.lang}_id_list.txt")
        self.save_list_to_file(missing_list, f"missing_{self.lang}_id_list.txt")
        if scraped_list:
            self.update_readme(max(scraped_list), lang=self.lang)
        logger.info(f"Downloaded {len(scraped_list)} cards; {len(missing_list)} had no page.")
