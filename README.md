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
    "subtitle": "",         [OPTIONAL]
                                <"Professor Sada">
    

}
```

Type symbols:
- ![Grass](img\types\Grass.svg) - `{G}`
- ![Fire](img\types\Fire.svg) - `{R}`
- ![Water](img\types\Water.svg) - `{W}`
- ![Lightning](img\types\Lightning.svg) - `{L}`
- ![Psychic](img\types\Psychic.svg) - `{P}`
- ![Fighting](img\types\Fighting.svg) - `{F}`
- ![Dark](img\types\Darkness.svg) - `{D}`
- ![Metal](img\types\Metal.svg) - `{M}`
- ![Fairy](img\types\Fairy.svg) - `{Y}`
- ![Dragon](img\types\Dragon.svg) - `{N}`
- ![Colorless](img\types\Colorless.svg) - `{C}`


## Downloaded data

- Info
    - Card content: `\data`
        - `\data\<generation>\<set>\<individual-card>.json`

- Image
    - Set package cover (Japanese version): See table [here](https://type-null.github.io/card/2024/02/timeline.html)


