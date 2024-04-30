"""
    Card class

    April 24, 2024 by Weihang
"""

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
]


class Card:
    def __init__(self):
        self.tags = []
        self.abilities = []
        self.attacks = []
        pass

    def add_tag(self, tag):
        self.tags.append(tag)

    def set_jp_id(self, id):
        self.jp_id = id

    def set_url(self, url):
        self.url = url

    def set_name(self, name):
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
        for tag in RULE_TAGS:
            if tag in rule:
                self.add_tag(tag)

    def set_stage(self, stage):
        self.stage = stage

    def set_level(self, level: int):
        self.level = level

    def set_hp(self, hp: int):
        self.hp = hp

    def set_types(self, types: list[str]):
        type_list = []
        self.types = types

    def add_ability(self, name, effect):
        self.abilities.append({"name": name, "effect": effect})

    def set_ancient_trait(self, name, effect):
        self.ancient_trait = {"name": name, "effect": effect}

    def set_evolve_from(self, pokemon):
        self.evolve_from = pokemon

    def add_attack(self, cost, name, damage, effect):
        self.attacks.append(
            {"cost": cost, "name": name, "damage": damage, "effect": effect}
        )
