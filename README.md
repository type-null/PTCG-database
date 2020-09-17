# PTCG-database

Scrape pokemon card game data from [Japan website](https://www.pokemon-card.com "test") and [US website](https://www.pokemon.com/us/pokemon-tcg/pokemon-cards/?cardName=&cardText=&evolvesFrom=&simpleSubmit=&format=unlimited&hitPointsMin=0&hitPointsMax=340&retreatCostMin=0&retreatCostMax=5&totalAttackCostMin=0&totalAttackCostMax=5&particularArtist=)

## Card Scraper (Japanese cards)
[see code](CardScraperJP.py)

Current Compatibility: XY-on 
Support card types:

| General | Compatible Types |
|:----------:|:-------------|
|**Trainers**|Supporter, Tool, Item, Stadium|
|**Energy**  |Basic, Special|
|**Pokémon** |Basic, Stage 1/2, EX, Break, GX, Prismstar, Shining (Hikaru), TagTeam GX, V, VMAX|

## Usage in Python
```python
import CardScraperJP

start, end = 35015, 38493
CardScraperJP.scrapeCards(start, end)
```
A progress bar will pop up:
```
[====                ] 21%	(1865/8495)
```

### Card ID
A unique number for each card in its web address.

For example, card "Shining Celebi"'s web address is `https://www.pokemon-card.com/card-search/details.php/card/34000` therefore `34000` is its card id.

But we noticed that, for some ids, it does not contain a card (out of range). This kind of web address will redirect to card-dex search index [page](https://www.pokemon-card.com/card-search/index.php). For the convenience of scraping, we also export the out-of-range ids in a separate csv.

| Regulation | Card Id Range|
|:----------:|:------------:|
|DP Energies|\[1,8\]|
|XY|\[33001, 38493\]

### Output
Outputs 2 `csv` files:
- `card_jp_<startID>_<endID>.csv` contains all the scraped cards information whose card-id between `startID` and `endID`.

    - **Schema**
    
        | Column      | Type   | Description                                 | Column      | Type   | Description                          |
        |-------------|--------|---------------------------------------------|-------------|--------|--------------------------------------|
        | cardId      | int    | Unique card address                         | waza1Cost   | list   | Cost of the first attack             |
        | cardType    | string | Type of the card (Pokémon, Supporter, etc.) | waza1Name   | string | Name of the first attack             |
        | name        | string | Card name                                   | waza1Damage | string | Base damage of the first attack      |
        | img         | string | Card image address                          | waza1Desc   | string | Description of the first attack      |
        | regulation  | string | Expansion pack name the card belongs to     | waza2Cost   | list   | Cost of the second attack            |
        | setNum      | int    | Number of the card in this expansion pack   | waza2Name   | string | Name of the second attack            |
        | setCount    | int    | Total number of cards in the same pack      | waza2Damage | string | Base damage of the second attack     |
        | rarity      | string | Rarity of the card                          | waza2Desc   | string | Description of the second attack     |
        | dexNum      | int    | National Pokédex number of the Pokémon      | GXCost      | list   | Cost of the GX attack                |
        | dexClass    | string | Classification of the Pokémon               | GXName      | string | Name of the GX attack                |
        | height      | float  | Height of the pokemon                       | GXDamage    | string | Base damage of the GX attack         |
        | weight      | float  | Weight of the pokemon                       | GXDesc      | string | Description of the GX attack         |
        | dexDesc     | string | Pokédex description of the Pokémon          | weakType    | string | Weakness to which type of Pokémon    |
        | author      | string | Illustrator of the card                     | weakValue   | string | Weakness value of the attack         |
        | desc        | string | Function of a Trainers card                 | resistType  | string | Resistance to which type of Pokémon  |
        | stage       | string | Pokémon evolution stage                     | resistValue | string | Resistance value of the attack       |
        | hp          | int    | Hit point                                   | escape      | int    | Number of energies needed to retreat |
        | pType       | list   | Pokémon type in this card                   | spRule      | string | Special rule of the card             |
        | ability     | string | Ability or Ancient Trait name               |             |        |                                      |
        | abilityDesc | string | Ability or Ancient Trait description        |             |        |                                      |
        
        
- `error_id_<startID>_<endID>.csv` contains all the card-id that do not contain a card between `startID` and `endID`. For example, [`32389`](https://www.pokemon-card.com/card-search/details.php/card/32389).

### Miscellaneous

- Wrong layout on web page (id=[37214](https://www.pokemon-card.com/card-search/details.php/card/37214)).
    Extra 'void' void energy (left) instead of '特別なルール' (special rule) (right).
    <p align="left">
      <img src="https://i.imgur.com/tlP9YKh.png" alt="wrong-void" width=400/>
      <img src="https://i.imgur.com/K0FWBVd.png" alt="right-sp-rule" width=400/>
    </p>
  
## Blueprint

- Scrape most recent Japanese pack cards (densetsu no kodou)
    - More packs
  
- Card language compatibility project
    - Add [Chinese card ver.](https://tw.portal-pokemon.com/card/)
  
- Create battle simulator (maybe Chinese ver.)
  - [TCG One](https://tcgone.net), [git repo](https://github.com/axpendix/tcgone-engine-contrib)
  - [バトルシミュレーター](https://www.pokemon-card.com/about/battle/)

- Train ML models on simulator to compose advanced decks, find better play strategies.

- Add 3D object rendered into battle game
