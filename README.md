# Pokémon Card Database

Card information for Pokemon TCG. Potential use for data analysis.



## Card Download 

>Official and unofficial sources, such as tcgo, tcgl, carddex, pokemon.com, pkmncards.com, etc. ([malie.io](https://malie.io/static/draft/html/pkproto_sv.html))

### English version

Info source: [pkmncards](www.pkmncards.com)

Image source: [malie.io](https://malie.io/static/)


### Japanese Version

Source: [Official Japan Pokemon Card Website](www.pokemon-card.com)


## Card Data

Good reference: [malie.io Pokémon Trading Card Game export format](https://malie.io/static/draft/html/pkproto_sv.html), it has great illustration of different fields.

Example:
```json
{
    "language": "en-US",    [REQUIRED]
    "jp_id": "",            [REQUIRED]
    "url": "https://pkmncards.com/card/golisopod-sun-moon-promos-smp-sm52/",
                            [REQUIRED]
    "img": "https://pkmncards.com/wp-content/uploads/en_US-Promo_SM-SM52-golisopod.jpg", 
                            [REQUIRED]
    "card_type": "Pokemon", [REQUIRED] 
                                <Pokemon/Trainer/Energy>
    "sub_type": ""          [OPTIONAL]
                                <Trainer: Item/Supporter/Stadium/Pokemon Tool>
                                <Energy: Basic/Special>
    "name": "Golisopod",    [REQUIRED]
    "illustrator": "Naoki Saito", 
                            [OPTIONAL]
    "regulation": "",       [OPTIONAL]
                                <A/B/C/D/E/F/G/...>
    "set_name": "SM PROMO", [REQUIRED]
    "set_img": "",          [OPTIONAL]
    "number": "SM52",       [REQUIRED]
    "rarity": "PROMO",      [OPTIONAL]
    "tags": [],             [OPTIONAL]
                                <Ancient/Future, Shiny, Tera>
    "ability": {
        "name": "Armor",
        "text": "This Pokémon takes 30 less damage from attacks (after applying Weakness and Resistance).",
    },                      [OPTIONAL]
    "attack": [
        {
            "cost": ["Grass", "Colorless", "Colorless"],
                                <Free>
            "name": "Resolute Claws",
            "damage": {
                "amount": 80,
                "suffix": "+",
                "prefix": "",
            },
            "text": "If your opponent’s Active Pokémon is a Pokémon-GX or a Pokémon-EX, this attack does 70 more damage (before applying Weakness and Resistance).",
        },
    ],                      [OPTIONAL]
    "reminder": "",         [OPTIONAL]
                                <You may play only 1 Supporter card during your turn.>
    "rule_box": {
        "name": "",             <Pokémon ex rule>
        "rule": "",             <When your Pokémon ex is Knocked Out, your opponent takes 2 Prize cards.>
    },                      [OPTIONAL]
    "effect": "",           [OPTIONAL]
                                <Search your deck for an Item card and a Pokémon Tool card, reveal them, and put them into your hand. Then, shuffle your deck.>
    "tera": "",             [OPTIONAL]
                                <As long as this Pokémon is on your Bench, prevent all damage done to this Pokémon by attacks (both yours and your opponent’s).>
    "stage": "STAGE1",      [REQUIRED]
    "evolution_text": "Evolves from Wimpod",
                            [REQUIRED]
    "hp": 130,              [REQUIRED]
    "types": ["Grass"],        [REQUIRED]
    "weakness": {
        "types": ["Fire"],
        "amount": 2,
        "operator": "x",
    },                       [OPTIONAL]
    "resistance": {
        "types": [],
        "amount": 0,
        "operator": "",
    },                      [OPTIONAL]
    "retreat": 2,           [REQUIRED]
    "flavor_text": "With a flashing slash of its giant sharp claws, it cleaves seawater—or even air—right in two.",
                            [OPTIONAL]
    "pokedex_number": 768,  [OPTIONAL]
    "pokemon_category": "Hard Scale Pokémon",
                            [OPTIONAL]
    "height": "6'07\"",     [OPTIONAL]
    "weight": "238.1 lbs",  [OPTIONAL]
}
```

Omitted:
- name
    - "subtitle": e.g., "Profesor Turo" in "Professor's Research"
    - "prefix": e.g., "Paldean" in Paldean Pokemon
    - "suffix": e.g., "with Grey Felt Hat" in Van Gogh Pikachu
- "copyright": {"text": "©2024 Pokémon / Nintendo / Creatures / GAME FREAK", ...}

Type symbols:
| ![Grass](img/types/Grass.svg) | ![Fire](img/types/Fire.svg) | ![Water](img/types/Water.svg) | ![Lightning](img/types/Lightning.svg) | ![Psychic](img/types/Psychic.svg) | ![Fighting](img/types/Fighting.svg) | ![Dark](img/types/Darkness.svg) | ![Metal](img/types/Metal.svg) | ![Fairy](img/types/Fairy.svg) | ![Dragon](img/types/Dragon.svg) | ![Colorless](img/types/Colorless.svg) |
|-------------------------------|-----------------------------|-------------------------------|--------------------------------------|-----------------------------------|-------------------------------------|---------------------------------|-------------------------------|-------------------------------|---------------------------------|-------------------------------------|
| `{G}`                         | `{R}`                       | `{W}`                         | `{L}`                                | `{P}`                             | `{F}`                               | `{D}`                           | `{M}`                         | `{Y}`                         | `{N}`                           | `{C}`                               |


Gender symbols: E.g., [Nidoran♀](https://www.pokemon-card.com/card-search/details.php/card/43350/) 
| UTF-8 | JSON unicode|
|-------|-------------|
|♀      |\u2640       |
|♂      |\u2642       |

English Rarity key, SV1-onwards:
| <img src="img/rarities/black_star_promo.svg" alt="promo" width="30"> | <img src="img/rarities/common.svg" alt="common" width="30"> | <img src="img/rarities/uncommon.svg" alt="uncommon" width="30"> | <img src="img/rarities/rare.svg" alt="rare" width="30"> | <img src="img/rarities/double_rare.svg" alt="double_rare" width="30"> | <img src="img/rarities/ultra_rare.svg" alt="ultra_rare" width="30"> | <img src="img/rarities/illustration_rare.svg" alt="illustration_rare" width="30"> | <img src="img/rarities/special_illustration_rare.svg" alt="special_illustration_rare" width="30"> | <img src="img/rarities/hyper_rare.svg" alt="hyper_rare" width="30"> | <img src="img/rarities/shiny_rare.svg" alt="shiny_rare" width="30"> | <img src="img/rarities/shiny_ultra_rare.svg" alt="shiny_ultra_rare" width="30"> | [ACE]         |
|-------------------------------------------------------------------------|--------------------------------------------------------------|----------------------------------------------------------------------|------------------------------------------------|------------------------------------------------------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------------|---------------|
| promo                                                                   | common                                                       | uncommon                                                             | rare                                           | double rare                                                               | ultra rare                                                           | illustration rare                                                             | special illustration rare                                                                 | hyper rare                                                           | shiny rare                                                           | shiny ultra rare                                                     | ace spec rare |

## Downloaded data

- Info
    - Card content: `\data`
        - `\data\<generation>\<set>\<individual-card>.json`

- Image
    - Set package cover (Japanese version): See table [here](https://type-null.github.io/card/2024/02/timeline.html)


