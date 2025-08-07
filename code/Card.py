"""
Card class

April 24, 2024 by Weihang
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


RULE_TAGS = [
    "ACE SPEC",
    "ex",
    "Tera",
    "かがやく",
    "Radiant",
    "VMAX",
    "VSTAR",
    "V-UNION",
    "V",
    "TAG TEAM",
    "プリズムスター",
    "Prism Star",
    "GX",
    "EX",
    "M進化",
    "Mega",
    "メガ",
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


class Card:
    def __init__(self):
        self.tags = []
        self.abilities = []
        self.attacks = []
        self.sources = []
        pass

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
        if not known_tag and self.card_type != "特殊エネルギー":
            logger.error(f"Card {self.out_id} has unseen rule box!")
        # Clean up
        if "LV.X" in self.tags:
            self.tags.remove("V")
        if "Prism Star" in self.tags:
            self.tags.remove("Star")
        if "獎賞卡" in rule:
            self.tags.remove("賞")

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
        if hasattr(self, "game"):
            card_dict["game"] = self.game
        if hasattr(self, "lang"):
            card_dict["lang"] = self.lang
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

        return card_dict

    def save(self, folder=""):
        card_dict = self.to_dict()

        if "jp_id" in card_dict:
            # Japanese
            folder = f"data_jp/{self.set_name}/"
            filename = str(self.jp_id) + ".json"
        elif hasattr(self, "game") and self.game == "TCG Pocket":
            # Pocket
            folder = f"data_pocket/{self.set_code}/"
            filename = self.number + ".json"
        elif hasattr(self, "lang") and self.lang == "tc":
            folder = f"data_tc/{self.set_name}/"
            filename = self.number + ".json"
        else:
            # English version
            if self.series:
                folder = f"data_en/{self.series}/{self.set_name}/"
            else:
                folder = f"data_en/{self.set_name}/"
            filename = self.number + ".json"

        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        # Check for duplicate filenames and append a number if necessary
        base, extension = os.path.splitext(path)
        counter = 2
        while os.path.exists(path):
            path = f"{base}-{counter}{extension}"
            counter += 1

        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(card_dict, json_file, indent=4, ensure_ascii=False)
