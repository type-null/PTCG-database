"""
    Read card info from the TCGdex API

    Some languages have no official card database that can be read the way
    pokemon-card.com or pokemoncard.co.kr can. TCGdex publishes those
    languages as JSON, with the full card text rather than only a picture,
    so it fills the gap for French, German, Spanish, Italian, Portuguese and
    Simplified Chinese.

    The wording of every field is the site's own, exactly as the other
    scrapers keep theirs.

    September 15, 2026 by Weihang
"""

import json
import sys

from loguru import logger
from tqdm import tqdm

import paths
from Card import Card
from CardScraper import CardScraper

API = "https://api.tcgdex.net/v2"

#: TCGdex language code -> folder suffix used under `data_`.
LANGS = {
    "fr": "fr",
    "de": "de",
    "es": "es",
    "it": "it",
    "pt": "pt",
    "zh-cn": "sc",  # Simplified Chinese
}


class CardScraperTCGdex(CardScraper):
    #: A JSON API answers faster than a rendered page, but this one is run by
    #: volunteers and starts returning 503 at roughly two requests a second,
    #: so leave more room between them than the sites can take.
    delay = 0.6

    def __init__(self, lang="fr", delay=None):
        super().__init__(delay=delay)
        if lang not in LANGS:
            raise ValueError(f"Unknown language {lang!r}; expected one of {sorted(LANGS)}")
        self.api_lang = lang
        self.lang = LANGS[lang]

    def card_url(self, card_id):
        return f"{API}/{self.api_lang}/cards/{card_id}"

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    def read_card(self, card_id, series=None):
        data = self.get_json(self.card_url(card_id))
        if data is None:
            logger.debug(f"Card {card_id} could not be read")
            return "Page not found"

        card = Card()
        card.set_lang(self.lang)
        card.set_url(self.card_url(card_id))
        card.set_out_id(card_id)
        card.set_card_name(data.get("name", ""))

        image = data.get("image")
        card.set_img(f"{image}/high.webp" if image else "")

        card.set_card_type(data.get("category", ""))
        sub_type = data.get("trainerType") or data.get("energyType")
        if sub_type:
            card.set_sub_type(sub_type)

        card_set = data.get("set") or {}
        total = (card_set.get("cardCount") or {}).get("total")
        card.set_set(card_set.get("id", "no_set"), card_set.get("symbol"))
        if card_set.get("name"):
            card.set_set_full_name(card_set["name"])
        card.set_collector(str(data.get("localId", "")), total)
        if series:
            card.set_set_extra(series.get("name"), card_set.get("name"), card_set.get("id"), series.get("date"))

        # The API writes the string "None" where a card has no rarity. Storing
        # that verbatim reads like a mistake, so record nothing instead.
        if data.get("rarity") and data["rarity"] != "None":
            card.set_rarity(data["rarity"])
        if data.get("regulationMark"):
            card.set_mark(data["regulationMark"])
        if data.get("illustrator"):
            card.set_author([data["illustrator"]])
        if data.get("hp"):
            card.set_hp(data["hp"])
        if data.get("types"):
            card.set_types(data["types"])
        if data.get("stage"):
            card.set_stage(data["stage"])
        if data.get("evolveFrom"):
            card.set_evolve_from(data["evolveFrom"])
        if data.get("effect"):
            card.set_effect(data["effect"])
        if data.get("description"):
            card.set_flavor_text(data["description"])
        if data.get("dexId"):
            card.set_pokedex(data["dexId"][0])
        if data.get("suffix"):
            card.add_tag(data["suffix"])
        if data.get("retreat") is not None:
            card.set_retreat(data["retreat"])

        for ability in data.get("abilities") or []:
            card.add_ability(ability.get("name", ""), ability.get("effect", ""))
        for attack in data.get("attacks") or []:
            card.add_attack(
                attack.get("cost") or [],
                attack.get("name", ""),
                attack.get("damage"),
                attack.get("effect", ""),
            )

        for field, setter in (("weaknesses", card.set_weakness), ("resistances", card.set_resistance)):
            entries = data.get(field) or []
            if entries:
                setter([entry.get("type") for entry in entries], entries[0].get("value"))

        card.add_source("TCGdex", self.card_url(card_id))
        card.save()
        del card
        return "Successfully scraped"

    # ------------------------------------------------------------------
    # Updating
    # ------------------------------------------------------------------

    def list_sets(self):
        """Every set the API publishes for this language."""
        sets = self.get_json(f"{API}/{self.api_lang}/sets")
        if not sets:
            logger.error("Could not list any set")
            return []
        return sets

    def set_cards(self, set_id):
        """Card ids of one set, with the series the set belongs to."""
        data = self.get_json(f"{API}/{self.api_lang}/sets/{set_id}")
        if data is None:
            logger.error(f"Could not open set {set_id}")
            return [], None
        series = data.get("serie") or {}
        series = {"name": series.get("name"), "date": data.get("releaseDate")}
        return [card["id"] for card in data.get("cards") or []], series

    def stored_card_urls(self):
        """Every card url already saved for this language."""
        urls = set()
        for path in paths.data_dir(self.lang).rglob("*.json"):
            try:
                urls.add(json.loads(path.read_text(encoding="utf-8")).get("url"))
            except (ValueError, OSError):
                logger.warning(f"Could not read {path}")
        urls.discard(None)
        return urls

    def update(self, limit=None):
        """Download every card the API lists that is not on disk yet."""
        logger.info(f"===== Updating started ({self.lang}) =====")

        sets = self.list_sets()
        if not sets:
            return
        logger.info(f"API lists {len(sets)} sets.")

        stored = self.stored_card_urls()
        logger.info(f"{len(stored)} cards already stored.")
        if limit:
            sets = sets[:limit]

        downloaded = 0
        for entry in tqdm(sets, desc=f"Checking {self.lang} sets", disable=None):
            card_ids, series = self.set_cards(entry["id"])
            declared = (entry.get("cardCount") or {}).get("total") or 0
            if declared and not card_ids:
                # The set index counts cards the API cannot actually serve, so
                # say so rather than let the language look larger than it is.
                logger.warning(f"Set {entry['id']} claims {declared} cards but serves none")
            missing = [c for c in card_ids if self.card_url(c) not in stored]
            for card_id in tqdm(missing, desc=f"Downloading {entry['id']}", leave=False, disable=None):
                if self.read_card_safely(card_id, series=series) == "Successfully scraped":
                    downloaded += 1
            if missing:
                logger.info(f"Set {entry['id']}: {len(card_ids)} listed, {len(missing)} downloaded.")

        logger.info(f"Downloaded {downloaded} cards.")


if __name__ == "__main__":
    sys.path.insert(0, str(paths.ROOT / "code"))
