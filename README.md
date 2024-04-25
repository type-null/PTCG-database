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
    "language": "en-US", [REQUIRED]
    "card_type": "Pokemon", [REQUIRED] <Pokemon/Trainer/Energy>
    "sub_type": "", [OPTIONAL]
        <Trainer: Item/Supporter/Stadium/Pokemon Tool>
        <Energy: Basic, Special>
    "name": "Golisopod", [REQUIRED]

}
```

## Downloaded data

- Info
    - Card content: `\data`
        - `\data\<generation>\<set>\<individual-card>.json`

- Image
    - Set package cover (Japanese version): See table [here](https://type-null.github.io/card/2024/02/timeline.html)


