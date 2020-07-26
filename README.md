# PTCG-database

Scrape pokemon card game data from [Japan website](https://www.pokemon-card.com) and [US website](https://www.pokemon.com/us/pokemon-tcg/pokemon-cards/?cardName=&cardText=&evolvesFrom=&simpleSubmit=&format=unlimited&hitPointsMin=0&hitPointsMax=340&retreatCostMin=0&retreatCostMax=5&totalAttackCostMin=0&totalAttackCostMax=5&particularArtist=)

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
