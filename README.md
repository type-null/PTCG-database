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
    "card_type": "Pokemon", [REQUIRED] 
                                <Pokemon/Trainer/Energy>
    "sub_type": "",         [OPTIONAL]
                                <Trainer: Item/Supporter/Stadium/Pokemon Tool>
                                <Energy: Basic, Special>
    "name": "Golisopod",    [REQUIRED]
    "illustrator": "Naoki Saito", [OPTIONAL]
    "regulation": "",       [OPTIONAL]
                                <A/B/C/D/E/F/G/...>
    "set": "SM PROMO",      [REQUIRED]
    "number": "SM52",       [REQUIRED]
    "rarity": "PROMO",      [OPTIONAL]
}
```
https://www.pokemon.com/us/pokemon-tcg/pokemon-cards/6?cardName=&cardText=&evolvesFrom=&format=unlimited&sv05=on&hitPointsMin=0&hitPointsMax=340&retreatCostMin=0&retreatCostMax=5&totalAttackCostMin=0&totalAttackCostMax=5&particularArtist=&advancedSubmit=

Omitted:
- name
    - subtitle: e.g., "Profesor Turo" in "Professor's Research"
    - prefix
    - suffix

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
| ![promo](img/rarities/black_star_promo.svg) | ![common](img/rarities/common.svg) | ![uncommon](img/rarities/uncommon.svg) | ![rare](img/rarities/rare.svg) | ![double_rare](img/rarities/double_rare.svg) | ![ultra_rare](img/rarities/ultra_rare.svg) | ![illustration_rare](img/rarities/illustration_rare.svg) | ![special_illustration_rare](img/rarities/special_illustration_rare.svg) | ![hyper_rare](img/rarities/hyper_rare.svg) | ![shiny_rare](img/rarities/shiny_rare.svg) | ![shiny_ultra_rare](img/rarities/shiny_ultra_rare.svg) | [ACE]         |
|---------------------------------------------|------------------------------------|----------------------------------------|--------------------------------|----------------------------------------------|--------------------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------------------|---------------|
| promo                                       | common                             | uncommon                               | rare                           | double rare                                  | ultra rare                                 | illustration rare                                        | special illustration rare                                                | hyper rare                                 | shiny rare                                 | shiny ultra rare                                       | ace spec rare |

## Downloaded data

- Info
    - Card content: `\data`
        - `\data\<generation>\<set>\<individual-card>.json`

- Image
    - Set package cover (Japanese version): See table [here](https://type-null.github.io/card/2024/02/timeline.html)


