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
    "かがやく",
    "VMAX",
    "VSTAR",
    "V-UNION",
    "V",
    "TAG TEAM",
    "プリズムスター",
    "GX",
    "EX",
    "M進化",
    "BREAK",
    "LEGEND",
    "レベルアップ",
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

    def set_jp_id(self, id):
        self.jp_id = id

    def set_url(self, url):
        self.url = url

    def set_card_name(self, name):
        self.name = name

    def set_img(self, url):
        self.img = url

    def set_card_type(self, card_type):
        self.card_type = card_type

    def set_set(self, name, url):
        self.set_name = name
        self.set_img = url

    def set_collector(self, num, tot):
        self.number = num
        self.set_total = tot

    def set_rarity(self, rarity, url):
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
        if not known_tag:
            logger.error(f"Card {self.jp_id} has unseen rule box!")

    def set_stage(self, stage):
        self.stage = stage

    def set_level(self, level: int):
        self.level = level

    def set_hp(self, hp: int):
        self.hp = hp

    def set_types(self, types: list[str]):
        self.types = types

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
            "jp_id": self.jp_id,
            "url": self.url,
            "name": self.name,
            "img": self.img,
            "card_type": self.card_type,
        }
        if self.tags:
            card_dict["tags"] = self.tags
        if hasattr(self, "set_name"):
            card_dict["set_name"] = self.set_name
            card_dict["set_img"] = self.set_img
        else:
            self.set_name = "no_set"
        if hasattr(self, "number"):
            card_dict["number"] = self.number
            card_dict["set_total"] = self.set_total
        if hasattr(self, "rarity"):
            card_dict["rarity"] = self.rarity
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

    def save(self, folder="data/"):
        card_dict = self.to_dict()

        folder = f"{folder + self.set_name}/"
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, str(self.jp_id) + ".json")
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(card_dict, json_file, indent=4, ensure_ascii=False)
