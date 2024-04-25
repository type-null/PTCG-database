"""
    Card class

    April 24, 2024 by Weihang
"""


class Card:
    def __init__(self) -> None:
        pass

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

    def set_rarity(self, rarity, url):
        self.rarity = rarity
        self.rarity_img = url

    def set_effect(self, effect):
        self.effect = effect
