"""
Card class

April 24, 2024 by Weihang
"""

import json

import cardkeys
import paths
from loguru import logger


def one_segment(name):
    """A field made safe to use as a single folder or file name.

    A card names its own folder, and a page can state something unexpected
    there: one Taiwanese promo gave its set as the printed `039/039`, whose
    separator turned one folder into two and lost the card, because the parent
    of the parent had never been made. A name is therefore kept to one segment,
    so a surprising field misfiles a card at worst and never drops it.
    """
    return name.replace("/", "-").replace("\\", "-").strip() or "no_set"

#: Substrings of a rule box that identify a card mechanic. Order matters:
#: the longest form of a family comes first so "V-UNION" is not read as "V".
RULE_TAGS = [
    "ACE SPEC",
    "ex",
    "Tera",
    "かがやく",
    "Radiant",
    "찬란한",
    "VMAX",
    "VSTAR",
    "V-UNION",
    "V",
    "TAG TEAM",
    "태그팀",
    "プリズムスター",
    "Prism Star",
    "프리즘스타",
    "GX",
    "EX",
    "Mega Evolution",
    "メガシンカ",
    "메가진화",
    "M進化",
    "Mega",
    "メガ",
    "超級進化",
    "ゲンシ",
    "Primal",
    "BREAK",
    "LEGEND",
    "レベルアップ",
    "LV.X",
    "☆",  # star
    "Star",
    "賞",  # event card
    "公式大会では使えない",  # Banned card
    "何枚でも",  # Arceus LV.100
    "レギュレーション",  # Mew: regulation statement
    "ポケモンのどうぐは",  # Pokemon Tool rule
    "サポートは",  # Supporter rule
    "スタジアムは",  # Stadium rule
    "Baby",
    "Shining",
    "稜柱之星",  # Prism Star
    "光輝",  # Radiant
]

#: Card types whose rule box is expected to be free text rather than a mechanic.
UNTAGGED_CARD_TYPES = {"特殊エネルギー", "特殊能量卡"}


class Card:
    def __init__(self):
        self.tags = []
        self.abilities = []
        self.attacks = []
        self.sources = []

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)

    def set_game(self, game):
        self.game = game

    def set_lang(self, lang):
        self.lang = lang

    def set_jp_id(self, id):
        self.jp_id = id
        self.set_out_id(self.jp_id)

    def set_en_id(self, id):
        self.en_id = id
        self.set_out_id(self.en_id)

    def set_ko_id(self, id):
        self.ko_id = id
        self.set_out_id(self.ko_id)

    def set_out_id(self, id):
        self.out_id = id

    def set_url(self, url):
        self.url = url

    def set_card_name(self, name):
        self.name = name

    def set_img(self, url):
        self.img = url

    def set_card_type(self, card_type):
        self.card_type = card_type

    def set_sub_type(self, sub_type):
        # Trainer: Item/Supporter/Stadium/Pokemon Tool; Energy: Basic/Special
        self.sub_type = sub_type

    def set_mark(self, mark):
        self.regulation = mark

    def set_set(self, name, url=None):
        self.set_name = name
        self.set_img = url

    def set_set_code(self, code):
        self.set_code = code

    def set_set_date(self, date):
        self.date = date

    def set_set_full_name(self, name):
        self.set_full_name = name

    def set_set_extra(self, series, set_full_name, set_code, date):
        self.series = series
        self.set_set_full_name(set_full_name)
        self.set_set_code(set_code)
        self.set_set_date(date)

    def set_collector(self, num, tot):
        self.number = num
        self.set_total = tot

    def set_sub_pack(self, pack):
        # TCG Pocket sub pack
        self.pack = pack

    def set_rarity(self, rarity, url=None):
        self.rarity = rarity
        self.rarity_img = url

    def set_effect(self, effect):
        self.effect = effect

    def set_author(self, author):
        self.author = author

    def set_pokedex(self, num=-1, category=""):
        self.pokedex_number = num
        self.pokemon_category = category

    def set_ht_wt(self, ht, wt):
        self.height = ht
        self.weight = wt

    def set_flavor_text(self, text):
        self.flavor_text = text

    def set_rule_box(self, rule):
        self.rule_box = rule
        known_tag = False
        for tag in RULE_TAGS:
            if tag in rule:
                self.add_tag(tag)
                known_tag = True
        if not known_tag and getattr(self, "card_type", None) not in UNTAGGED_CARD_TYPES:
            # Not an error: a rule box we cannot tag is still stored in full.
            logger.warning(f"Card {getattr(self, 'out_id', '?')} has an untagged rule box: {rule[:60]}")
        # Clean up
        if "LV.X" in self.tags and "V" in self.tags:
            self.tags.remove("V")
        if "Prism Star" in self.tags and "Star" in self.tags:
            self.tags.remove("Star")
        if "獎賞卡" in rule and "賞" in self.tags:
            self.tags.remove("賞")
        if "Mega Evolution" in self.tags and "Mega" in self.tags:
            self.tags.remove("Mega")
        if "メガシンカ" in self.tags and "メガ" in self.tags:
            self.tags.remove("メガ")

    def set_mega_evolves_from(self, pokemon):
        """The Pokémon this Mega Evolution card is the Mega-Evolved form of."""
        self.mega_evolves_from = pokemon
        self.add_tag("Mega Evolution")

    def set_stage(self, stage):
        self.stage = stage

    def set_level(self, level: int):
        self.level = level

    def set_hp(self, hp: int):
        self.hp = hp

    def set_types(self, types: list[str]):
        self.types = types

    def set_tera(self, lang="jp"):
        if lang == "tc":
            self.tera_effect = "只要這隻寶可夢在備戰區，不會受到招式的傷害。"
        elif lang == "jp":
            self.tera_effect = (
                "このポケモンは、ベンチにいるかぎり、ワザのダメージを受けない。"
            )
        elif lang == "en":
            self.tera_effect = "As long as this Pokémon is on your Bench, prevent all damage done to this Pokémon by attacks (both yours and your opponent’s)."
        elif lang == "ko":
            self.tera_effect = "이 포켓몬은 벤치에 있는 한 기술의 데미지를 받지 않는다."
        else:
            logger.error(f"Unseen `lang` ({lang}) when setting tera!")
        self.add_tag("Tera")

    def set_ex_rule_tc(self):
        # Some Traditional Chinese card websites do not state 'ex rule' explicitly
        self.rule_box = "寶可夢【ex】【昏厥】時，對手獲得2張獎賞卡。"
        self.add_tag("ex")

    def set_technical_machine(self, rule):
        self.technical_machine_rule = rule

    def add_ability(self, name, effect):
        self.abilities.append({"name": name, "effect": effect})

    def set_ancient_trait(self, name, effect):
        self.ancient_trait = {"name": name, "effect": effect}

    def set_poke_power(self, name, effect):
        self.poke_power = {"name": name, "effect": effect}

    def set_poke_body(self, name, effect):
        self.poke_body = {"name": name, "effect": effect}

    def set_held_item(self, item, effect):
        self.held_item = {"item": item, "effect": effect}

    def set_held_berry(self, berry, effect):
        self.held_berry = {"berry": berry, "effect": effect}

    def set_evolve_from(self, pokemon):
        self.evolve_from = pokemon

    def add_attack(self, cost, name, damage, effect):
        if "GX" in name:
            self.add_tag("GX")
        self.attacks.append(
            {"cost": cost, "name": name, "damage": damage, "effect": effect}
        )

    def add_source(self, name, link):
        self.sources.append({"name": name, "link": link})

    def set_vstar_power_ability(self, name, effect):
        self.add_tag("VSTAR")
        self.vstar_power = {"type": "Ability", "name": name, "effect": effect}

    def set_vstar_power_attack(self, cost, name, damage, effect):
        self.add_tag("VSTAR")
        self.vstar_power = {
            "type": "Attack",
            "cost": cost,
            "name": name,
            "damage": damage,
            "effect": effect,
        }

    def set_weakness(self, weak_types, weak_value):
        self.weakness = {"type": weak_types, "value": weak_value}

    def set_resistance(self, weak_types, weak_value):
        self.resistance = {"type": weak_types, "value": weak_value}

    def set_retreat(self, num):
        self.retreat = num

    def to_dict(self):
        card_dict = {
            "url": self.url,
            "name": self.name,
            "img": self.img,
            "card_type": self.card_type,
        }
        if hasattr(self, "jp_id"):
            card_dict["jp_id"] = self.jp_id
        if hasattr(self, "en_id"):
            card_dict["en_id"] = self.en_id
        if hasattr(self, "ko_id"):
            card_dict["ko_id"] = self.ko_id
        if hasattr(self, "game"):
            card_dict["game"] = self.game
        if hasattr(self, "lang"):
            card_dict["lang"] = self.lang
        if hasattr(self, "sub_type"):
            card_dict["sub_type"] = self.sub_type
        if self.tags:
            card_dict["tags"] = self.tags
        if hasattr(self, "regulation"):
            card_dict["regulation"] = self.regulation
        if hasattr(self, "set_name"):
            card_dict["set_name"] = self.set_name
            if self.set_img:
                card_dict["set_img"] = self.set_img
        else:
            self.set_name = "no_set"
        if hasattr(self, "set_full_name"):
            card_dict["set_full_name"] = self.set_full_name
        if hasattr(self, "series"):
            card_dict["series"] = self.series
            card_dict["set_code"] = self.set_code
            card_dict["date"] = self.date
        if hasattr(self, "number"):
            card_dict["number"] = self.number
            card_dict["set_total"] = self.set_total
        if hasattr(self, "pack"):
            # TCG Pocket sub-pack
            card_dict["pack"] = self.pack
        if hasattr(self, "rarity"):
            card_dict["rarity"] = self.rarity
            if self.rarity_img:
                card_dict["rarity_img"] = self.rarity_img
        if hasattr(self, "effect"):
            card_dict["effect"] = self.effect
        if hasattr(self, "author"):
            card_dict["author"] = self.author
        if hasattr(self, "pokedex_number"):
            card_dict["pokedex_number"] = self.pokedex_number
            card_dict["pokemon_category"] = self.pokemon_category
        if hasattr(self, "height"):
            card_dict["height"] = self.height
            card_dict["weight"] = self.weight
        if hasattr(self, "flavor_text"):
            card_dict["flavor_text"] = self.flavor_text
        if hasattr(self, "stage"):
            card_dict["stage"] = self.stage
        if hasattr(self, "level"):
            card_dict["level"] = self.level
        if hasattr(self, "hp"):
            card_dict["hp"] = self.hp
        if hasattr(self, "types"):
            card_dict["types"] = self.types
        if hasattr(self, "tera_effect"):
            card_dict["tera_effect"] = self.tera_effect
        if hasattr(self, "technical_machine_rule"):
            card_dict["technical_machine_rule"] = self.technical_machine_rule
        if hasattr(self, "ancient_trait"):
            card_dict["ancient_trait"] = self.ancient_trait
        if hasattr(self, "poke_power"):
            card_dict["poke_power"] = self.poke_power
        if hasattr(self, "poke_body"):
            card_dict["poke_body"] = self.poke_body
        if hasattr(self, "held_item"):
            card_dict["held_item"] = self.held_item
        if hasattr(self, "held_berry"):
            card_dict["held_berry"] = self.held_berry
        if self.abilities:
            card_dict["abilities"] = self.abilities
        if self.attacks:
            card_dict["attacks"] = self.attacks
        if hasattr(self, "vstar_power"):
            card_dict["vstar_power"] = self.vstar_power
        if hasattr(self, "rule_box"):
            card_dict["rule_box"] = self.rule_box
        if hasattr(self, "mega_evolves_from"):
            card_dict["mega_evolves_from"] = self.mega_evolves_from
        if hasattr(self, "weakness"):
            card_dict["weakness"] = self.weakness
        if hasattr(self, "resistance"):
            card_dict["resistance"] = self.resistance
        if hasattr(self, "retreat"):
            card_dict["retreat"] = self.retreat
        if hasattr(self, "evolve_from"):
            card_dict["evolve_from"] = self.evolve_from
        if self.sources:
            card_dict["sources"] = self.sources

        # Some sources file part of what they publish in the wrong place. Fix
        # that before the keys are derived, so a card links on corrected fields.
        self.normalize_fields(card_dict)

        # Derived from the fields above, so a card downloaded tomorrow links to
        # its other printings without anything having to be rebuilt.
        card_dict.update(cardkeys.keys_for(card_dict))

        return card_dict

    @staticmethod
    def normalize_fields(card_dict):
        """Correct three ways a source's markup misfiles what it publishes.

        A skill block with no name, no cost and no damage is not an attack. The
        Traditional Chinese site closes most cards with an empty one, and files
        a trainer rule in an unnamed one; that text is a rule, so it becomes the
        rule box when the card has none.

        A rule box and an attack's effect are never the same sentence. Where
        they are, one is a copy: a card carrying a mechanic tag owns the rule,
        so the attack's effect is the copy, and a card with no tag at all has a
        rule box that was copied out of its own attack.

        Returns what it corrected, so a repair can report it.
        """
        fixed = []
        real, unnamed = [], []
        for attack in card_dict.get("attacks") or []:
            if (attack.get("name") or "").strip() or attack.get("cost") or attack.get("damage"):
                real.append(attack)
            else:
                unnamed.append(attack)

        if unnamed:
            stored = {
                (card_dict.get("effect") or "").strip(),
                (card_dict.get("rule_box") or "").strip(),
            }
            for block in unnamed:
                text = (block.get("effect") or "").strip()
                if text and text not in stored and not card_dict.get("rule_box"):
                    card_dict["rule_box"] = text
                    stored.add(text)
                    fixed.append("read the rule box from an unnamed block")
            if real:
                card_dict["attacks"] = real
            else:
                card_dict.pop("attacks", None)
            fixed.append(f"dropped {len(unnamed)} unnamed attack(s)")

        rule_box = (card_dict.get("rule_box") or "").strip()
        copies = [a for a in real if (a.get("effect") or "").strip() == rule_box]
        if rule_box and copies:
            if card_dict.get("tags"):
                for attack in copies:
                    attack["effect"] = None
                fixed.append("cleared an attack effect that only repeated the rule box")
            else:
                card_dict.pop("rule_box", None)
                fixed.append("dropped a rule box copied out of an attack")
        return fixed

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def destination(self):
        """Folder and file name this card belongs in."""
        # Some pages state no set at all — a handful of basic Energy cards.
        # They belong together in `no_set`, not loose in the language's root.
        set_folder = one_segment(str(getattr(self, "set_name", "") or "no_set"))
        if hasattr(self, "jp_id"):
            return paths.data_dir("jp") / set_folder, f"{self.jp_id}.json"
        # A card whose page states no collector number still needs a name.
        number = getattr(self, "number", None) or self.out_id
        if hasattr(self, "game") and self.game == "TCG Pocket":
            return paths.data_dir("pocket") / str(self.set_code), f"{number}.json"
        if getattr(self, "lang", None) == "ko":
            return paths.data_dir("ko") / set_folder, f"{number}.json"
        if getattr(self, "lang", None) not in (None, "en"):
            # Traditional Chinese and the other Pokémon Asia locales.
            return paths.data_dir(self.lang) / set_folder, f"{number}.json"
        if getattr(self, "series", None):
            return paths.data_dir("en") / self.series / set_folder, f"{number}.json"
        return paths.data_dir("en") / set_folder, f"{number}.json"

    def claim_path(self, directory, filename):
        """Pick the file this card owns.

        A card keeps the file holding its own url, so re-scraping updates a
        card in place instead of leaving `-2`, `-3`, ... copies behind. A
        genuinely different card whose number collides still gets its own
        numbered file.
        """
        stem = filename[: -len(".json")]
        candidate = directory / filename
        counter = 2
        while candidate.exists():
            try:
                existing = json.loads(candidate.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return candidate
            if existing.get("url") == self.url:
                return candidate
            candidate = directory / f"{stem}-{counter}.json"
            counter += 1
        return candidate

    def save(self, folder="", merge=True):
        """Write this card to disk and return the path written.

        `merge` keeps fields an earlier scrape stored that this one did not
        produce, so re-running a scraper never loses information.
        """
        card_dict = self.to_dict()
        directory, filename = self.destination()
        # The file is named after a printed field, and a printed field can hold
        # anything: one Taiwanese promo states its number as "039/M-P", whose
        # separator would place the card a directory below the one just made and
        # lose it. The name is kept to one segment so that cannot happen.
        filename = one_segment(filename)
        directory.mkdir(parents=True, exist_ok=True)
        path = self.claim_path(directory, filename)

        if merge and path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                existing = {}
            kept = [key for key in existing if key not in card_dict]
            if kept:
                logger.debug(f"Keeping {kept} from the earlier scrape of {path.name}")
                for key in kept:
                    card_dict[key] = existing[key]

                # A kept field can be one the normalisation above just removed,
                # so correct the merged record again rather than let an earlier
                # run's mistake come back, and derive its keys from the result.
                if self.normalize_fields(card_dict):
                    for key in ("print_key", "card_key"):
                        card_dict.pop(key, None)
                    card_dict.update(cardkeys.keys_for(card_dict))

        path.write_text(
            json.dumps(card_dict, indent=4, ensure_ascii=False), encoding="utf-8"
        )
        return path
