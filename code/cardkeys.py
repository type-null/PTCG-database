"""
Identity keys that link one card to its other printings.

Two cards can be "the same card" in two different ways, and they need two
different keys:

`print_key` is the exact one. Japan, Korea, Taiwan and the other Pokémon Asia
regions all number a set the same way, so `M6a 018` names one printing in all
of them — ピカチュウ, 피카츄 and 皮卡丘 are that same card. The languages TCGdex
serves likewise share one set id and number. English and TCG Pocket number
their own way, so they keep their own namespace.

`card_key` is the best-effort one, and it reaches across those families and
across rarities. What survives translation is the arithmetic and the artist:
Pokédex number, HP, retreat cost, illustrator, and the damage and cost pattern
of the attacks. A Pokémon printed twice — once common, once illustration rare,
or once in Japanese and once in French — keeps all of those.

A Trainer or an Energy card has no Pokédex number, HP or attacks to fingerprint,
so it gets no `card_key` at all rather than a guessed one.

September 16, 2026 by Weihang
"""

import json
import re
import unicodedata
from pathlib import Path

#: English species name -> national Pokédex number, taken from PokéAPI once.
SPECIES = json.loads((Path(__file__).parent / "species_dex.json").read_text(encoding="utf-8"))


def _load_intl():
    """Species names in the other languages, if that table has been fetched."""
    try:
        return json.loads((Path(__file__).parent / "species_dex_intl.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


#: language -> {species name -> dex}, for languages whose cards carry no number.
SPECIES_BY_LANG = _load_intl()

#: Which of those tables to read for a card of a given language. PokéAPI
#: publishes no Chinese species names, so Traditional and Simplified Chinese
#: have no name table — they need none in practice, because those sites state
#: the Pokédex number outright on 98% and 82% of their cards.
TABLES = {
    "jp": ("ja",),
    "ko": ("ko",),
    "fr": ("fr",),
    "de": ("de",),
    "es": ("es",),
    "it": ("it",),
    "pt": ("en",),
    "en": ("en",),
}

#: Names sorted longest first, so リザードン wins over リザード. Built once per table.
_LONGEST = {}

#: Each table again with its accents dropped, built once. The sources disagree
#: with themselves about accents: the French table spells Évoli, Élektek and
#: Morphéo with them while the cards print Evoli, Elektek and Morpheo without,
#: and a lookup that keeps the accents on one side only can never match. Folding
#: both sides is what closes that — measured at 170 French cards, 96 of them
#: distinct names, that could not be placed before.
_FOLDED = {}


#: Tables that must not be folded. Japanese writes a dakuten as a combining
#: mark, so dropping it turns ガラガラ into カラカラ — Marowak into Cubone, a
#: different Pokémon. Kana carry meaning in their marks; Latin accents, in these
#: sources, do not.
UNFOLDABLE = {"ja"}


def folded_table(table_name, table):
    """`table` keyed a second time with the accents and punctuation dropped.

    The punctuation matters as much as the accents: every table spells the bird
    `farfetch’d` with a curly apostrophe, while a card prints it straight, and
    the name is looked up with its apostrophes taken out. Taking them out of
    both sides is what lets the two meet.
    """
    if table_name in UNFOLDABLE:
        return {}
    if table_name not in _FOLDED:
        _FOLDED[table_name] = {plain_marks_out(plain_letters(name)): dex for name, dex in table.items()}
    return _FOLDED[table_name]


def plain_marks_out(text):
    """`text` without the punctuation a name is looked up without."""
    return text.replace("’", "").replace("'", "").replace(".", "").replace(":", "")


def longest_species_in(text, table_name):
    """The longest species name of that table occurring in `text`.

    Japanese, Korean and Chinese card names run the species together with
    everything else — ナンジャモのズピカ, メガリザードンXex — so the species is found
    by looking for it inside the name rather than by splitting words.

    Both sides are folded to one character width first. The species table spells
    them ポリゴン２ and ポリゴンｚ while the cards print ポリゴン2 and ポリゴンZ, and
    without folding neither matches — leaving only ポリゴン, which is a different
    Pokémon. Folded, disagreement with Japan's own published numbers falls from
    0.22% to 0.01%.
    """
    if table_name not in _LONGEST:
        names = SPECIES_BY_LANG.get(table_name, {})
        _LONGEST[table_name] = sorted(
            ((unicodedata.normalize("NFKC", name).lower(), dex) for name, dex in names.items()),
            key=lambda pair: -len(pair[0]),
        )
    folded = unicodedata.normalize("NFKC", text).lower()
    for name, dex in _LONGEST[table_name]:
        if len(name) > 1 and name in folded:
            return dex
    return None

#: What a card name wraps around its species: regional forms and mechanics.
FORM = r"^(mega|alolan|galarian|hisuian|paldean|white|black|dark|light|shining|radiant|shiny)\s+"
MECHANIC = r"\s+(ex|v|vmax|vstar|v-union|gx|break|prime|lv\.x|star|δ|◇|tag team|legend)$"

#: Regions that share Japan's set codes and numbering. Simplified Chinese is
#: read from TCGdex but numbered as Japan numbers — its sets are SV7, SV8, SV10
#: — so it belongs here on its numbering alone. It used to say that 541 of the
#: 829 positions Japan also holds are provably the same Pokémon; that proved
#: nothing, because TCGdex answers zh-cn with Taiwan's text, so the comparison
#: was Taiwan against Japan and not Simplified Chinese against anything.
ASIA = {"jp", "ko", "tc", "hk", "th", "id", "sg", "my", "ph", "sc"}

#: Languages TCGdex numbers its own way, sharing one set id across all of them.
TCGDEX = {"fr", "de", "es", "it", "pt"}


#: TCG Pocket names its sets A1, A1a, A2 … and its promos P-A. TCGdex serves
#: those sets under every language it carries, using the same ids, so a Pocket
#: card is the same printing in all of them. The pattern is read only for Pocket
#: data and the TCGdex languages: English's own Base Set 2 is "B2", and is not a
#: Pocket set.
POCKET_SET = re.compile(r"(?:A|B)\d+[a-z]?|P-[A-Z]")


def family(card):
    """Which numbering scheme this card belongs to."""
    if card.get("game") == "TCG Pocket":
        return "pocket"
    lang = card.get("lang") or ("jp" if "jp_id" in card else "en")
    if lang in ASIA:
        return "asia"
    if lang in TCGDEX:
        code = str(card.get("set_code") or card.get("set_name") or "")
        return "pocket" if POCKET_SET.fullmatch(code) else "tcgdex"
    return lang


#: Taiwan prints some of Japan's sets under its own spelling, with a trailing
#: "F" that is sometimes spaced. The cards are the same printing: across these
#: five sets, 469 shared numbers are the same Pokémon and none is a different
#: one. Only these are aliased — Japan has sets genuinely called SVF and MF.
SET_ALIAS = {
    "SV11BF": "SV11B",
    "SV2a F": "SV2a",
    "SV3 F": "SV3",
    "SV9aF": "SV9a",
    "SVP1 F": "SVP1",
}

#: Korea spells twenty of Japan's set codes in lower case, and for these twenty
#: the cards behind them are the same printings: every number the two share
#: fingerprints alike and not one disagrees. They are listed rather than folded
#: by case, because case is not the question — of the 53 pairs that differ only
#: in case, 33 are different sets. `CP6` and `cp6` agree on 23 numbers and
#: disagree on 49; `Bd` and `bd` agree on none of their 6 and disagree on all.
SET_ALIAS.update({
    "cp2": "CP2", "cp5": "CP5", "sm2k": "SM2K", "sm2l": "SM2L", "sm4a": "SM4A",
    "sm4s": "SM4S", "sm6b": "SM6b", "sm8": "SM8", "sm9a": "SM9a", "smL": "SML",
    "smd": "SMD", "sme": "SME", "smp2": "SMP2", "x30": "X30", "xy4": "XY4",
    "xya": "XYA", "xyb": "XYB", "xyc": "XYC", "xyf": "XYF", "y30": "Y30",
})


#: Promo series each region numbers for itself. Japan and Taiwan both publish an
#: `S-P`, an `SV-P` and an `M-P`, and they are not the same cards: across 465
#: shared numbers exactly one fingerprint agrees and 169 disagree — Japan's S-P
#: 071 is シャワーズ where Taiwan's is 嘟嘟利V. Keyed as one family they published
#: 463 links between cards that have nothing to do with each other. Korea's SVP1
#: is left alone: there all 7 shared numbers agree and none disagree.
REGIONAL_PROMO = {"S-P", "SV-P", "M-P"}


def print_key(card):
    """The printing this card is, shared by every language that numbers it alike.

    A card whose "number" is not a number identifies nothing: several Japanese
    promos are numbered with their own set code, and one is numbered "n/a".
    Those get no print key rather than a key that lumps them together.
    """
    code = card.get("set_code") or card.get("set_name")
    code = SET_ALIAS.get(str(code), code)
    number = printed_number(card.get("number"))
    if not code or not number:
        return None
    if not any(char.isdigit() for char in number) or number == str(code):
        return None
    group = family(card)
    if group == "asia" and str(code) in REGIONAL_PROMO:
        # Numbered per region, so the language is part of the printing's name.
        group = card.get("lang") or ("jp" if "jp_id" in card else group)
    return f"{group}:{code}-{number}"


def printed_number(number):
    """The number a printing is identified by, without leading zeros.

    One source writes 001 where another writes 1 for the very same card, and no
    set numbers two different cards 01 and 1, so the zeros carry nothing.
    """
    return re.sub(r"^0+(?=\d)", "", str(number or ""))


#: The same mark, written differently by different sites: TCGdex writes `120+`
#: where the Japanese, Korean and Chinese sites write the full-width `120＋`,
#: and `x2` against `×2`. Folded, one card fingerprints alike everywhere —
#: measured at 3,497 more cards reaching another language.
WIDE_MARKS = {"＋": "+", "×": "x", "✕": "x", "－": "-", "−": "-", "ー": "-"}


def plain_marks(text):
    return "".join(WIDE_MARKS.get(mark, mark) for mark in str(text))


def damage_of(attack):
    """One attack's damage, however the source happens to write it.

    An attack that deals no damage is written three ways: Japan, Korea, English
    and the TCGdex languages leave the field null, Taiwan writes an empty string,
    and a few records carry the word as text. Rendered into a fingerprint those
    became `None` against ``, so one card keyed two ways and the two never met —
    measured at 14,936 language-pair links, 1,890 of them between Japan and
    Taiwan and 1,881 between English and Taiwan.
    """
    damage = attack.get("damage")
    if isinstance(damage, dict):
        return plain_marks(f"{damage.get('amount')}{damage.get('suffix') or ''}")
    if damage is None or str(damage).strip() in ("", "None"):
        return ""
    return plain_marks(damage)


def plain_letters(text):
    """`text` with its accents dropped, the way PokéAPI spells its own names.

    The table writes Flabébé as `flabebe`. This is only ever tried as a second
    spelling: the French, German, Spanish and Italian tables spell their species
    with the accents kept, and folding those away first would stop them matching.
    """
    bare = unicodedata.normalize("NFKD", text)
    return "".join(letter for letter in bare if not unicodedata.combining(letter))


def name_candidates(stripped):
    """Every run of neighbouring words in a name, longest first.

    A card name wraps its species in words no species table holds: "Dusk Mane
    Necrozma", "Origin Forme Palkia", "M Charizard EX", "Special Delivery
    Charizard", "Snow-cloud Castform". Reading each run of neighbouring words
    finds the species without keeping a list of every prefix the game has ever
    printed.

    The whole name is tried before any part of it, so a species whose own name
    runs to two words — Mr. Mime, Tapu Koko, Type: Null — still wins over either
    half. Runs of one word are read left to right, which is what keeps a TAG TEAM
    card like "Pikachu & Zekrom-GX" naming the first of the two.
    """
    # PokéAPI spells the two Nidoran `nidoran-f` and `nidoran-m`, while every
    # per-language table spells them `nidoran♀` and `nidoran♂`. Both spellings
    # are offered, so whichever table is read finds its own.
    letters = stripped.replace("♂", "-m").replace("♀", "-f")
    found = []
    for spelling in dict.fromkeys((stripped, letters, plain_letters(stripped))):
        words = [word for word in spelling.split("-") if word]
        for length in range(len(words), 0, -1):
            for start in range(len(words) - length + 1):
                candidate = "-".join(words[start : start + length])
                if candidate not in found:
                    found.append(candidate)
    return found


def nidoran_gender(stripped):
    """Nidoran's gender written the way the tables spell it.

    It is the one species whose name ends in a symbol, and the sources write that
    symbol every way they can: `Nidoran ♂`, and in German `Nidoran M` and
    `Nidoran W`. The tables keep it as `nidoran♂` and `nidoran♀` with nothing in
    between, so all of them are read as that.

    This runs after the mechanics have been taken off the end, or a delta species
    — `Nidoran M δ` — would still end in its δ when the gender is looked for.
    """
    if "nidoran" not in stripped:
        return stripped
    # A space or nothing at all before the symbol, but never a hyphen: PokéAPI's
    # own table spells them `nidoran-m` and `nidoran-f`, and reading that final
    # letter as the gender would rewrite a name that already matched.
    # The gender is written every way the sources can: `Nidoran ♂`, `Nidoran♂`
    # flush against the name in TCG Pocket, and the German `Nidoran M` and
    # `Nidoran W`. Read in two steps, because the order is what keeps them apart:
    # a letter becomes the symbol only when a space separates it, which leaves
    # PokéAPI's own `nidoran-m` alone, and only then is the space closed up.
    stripped = re.sub(r"\s+m$", " ♂", stripped)
    stripped = re.sub(r"\s+w$", " ♀", stripped)
    return re.sub(r"\s+([♂♀])$", r"\1", stripped)


def dex_from_name(name, lang="en"):
    """The national Pokédex number a card name points at.

    Several sources publish no Pokédex number — pkmncards, TCG Pocket, and many
    Japanese and Korean cards — so the species has to be read out of the name:
    "Iono's Tadbulb" is Tadbulb, 938, and ナンジャモのズピカ is the same card.
    A name this cannot place returns nothing, so the card goes unfingerprinted
    rather than joining the wrong group.
    """
    if not name:
        return None

    text = name.lower().replace("’", "'")
    text = re.sub(r"\s*\([^)]*\)", "", text)  # "(Delta Species)"

    # Latin scripts: peel the wrapping off and look the species up whole.
    stripped = re.sub(r"^[a-z.\- ]+?'s\s+", "", text)  # "Iono's", "Rocket's"
    # PokéAPI spells them farfetchd, mr-mime, nidoran-f: no apostrophe, no dot,
    # and the gender written as a letter.
    stripped = re.sub(r"\s+female$", "-f", stripped)
    stripped = re.sub(r"\s+male$", "-m", stripped)
    stripped = stripped.replace("'", "").replace(".", "").replace(":", "")
    # A card naming several Pokémon separates them with commas — "Arceus, Dialga
    # et Palkia GX". The comma is not part of a name, and leaving it attached
    # stops the first Pokémon matching, which hands the card to the second one.
    stripped = stripped.replace(",", " ")
    stripped = re.split(r"\s+(?:de|von|di|del)\s+", stripped)[0]  # "Têtampoule de Mashynn"
    for _ in range(3):  # a name can carry both a form and a mechanic
        stripped = re.sub(FORM, "", stripped)
        stripped = re.sub(MECHANIC, "", stripped)
    stripped = nidoran_gender(stripped)
    stripped = stripped.strip().replace(" ", "-")

    for table_name in TABLES.get(lang, ("en",)):
        table = SPECIES if table_name == "en" else SPECIES_BY_LANG.get(table_name, {})
        candidates = name_candidates(stripped)
        for candidate in candidates:
            if candidate in table:
                return table[candidate]
        # Only once the name has failed as printed: a table that keeps its
        # accents is still read first, so nothing that matched before changes.
        bare = folded_table(table_name, table)
        for candidate in candidates:
            if candidate in bare:
                return bare[candidate]

    # Japanese, Korean and Chinese names carry no spaces to split on.
    for table_name in TABLES.get(lang, ()):
        if table_name != "en":
            found = longest_species_in(name.lower(), table_name)
            if found:
                return found
    return None


def stated_dex(raw):
    """The Pokédex number a source states, as a plain number.

    A few Japanese pages print it as `No.491`, and a fingerprint is built from
    text: `No.491|180|2|...` and `491|180|2|...` are the same card written two
    ways, and neither would ever find the other. Reading the digits out settles
    it — measured at seven cards reaching other languages, two of them reaching
    nine.

    `-1` and `0` are how a source says it states no number at all, so they are
    treated as no number rather than as a Pokémon.
    """
    if raw in (None, ""):
        return None
    text = str(raw).strip()
    # `-1` means "no number", and stripping the punctuation out of it would read
    # it as 1 — fingerprinting the card as Bulbasaur.
    if text.startswith("-"):
        return None
    digits = re.sub(r"\D", "", text)
    found = int(digits) if digits else None
    return found if found and found > 0 else None


def card_key(card):
    """A fingerprint every printing of the same Pokémon card shares.

    Every part is written as text, because one source stores HP as a number
    and another as a string for the very same card. The Pokédex number is what
    keeps the fingerprint honest — without it, cards that merely share an
    artist and a damage figure collapse together — so where a source omits it,
    the species is read from the name instead.
    """
    hp, author = card.get("hp"), card.get("author")
    lang = card.get("lang") or ("jp" if "jp_id" in card else "en")
    dex = stated_dex(card.get("pokedex_number")) or dex_from_name(card.get("name"), lang)
    attacks = card.get("attacks") or []
    if not dex or not hp or not author or not attacks:
        return None

    authors = author if isinstance(author, list) else [author]
    return "|".join(
        [
            str(dex),
            str(hp),
            str(card.get("retreat")),
            "/".join(sorted(str(name) for name in authors)),
            ",".join(damage_of(attack) for attack in attacks),
            ",".join(str(len(attack.get("cost") or [])) for attack in attacks),
        ]
    )


#: Punctuation differs between printings of one name — Traditional Chinese
#: stores 奇樹的光蚪仔 both with and without its angle brackets — so names are
#: compared with all of it stripped away.
NAME_NOISE = re.compile(r"[^0-9A-Za-z぀-ヿ㐀-鿿가-힯]")


def bare_name(name):
    return NAME_NOISE.sub("", unicodedata.normalize("NFKC", name or "")).lower()


def names_per_language(entries):
    """The most distinct names any single language contributes to a group."""
    names = {}
    for lang, name, *_ in entries:
        names.setdefault(lang, set()).add(bare_name(name))
    return max((len(found) for found in names.values()), default=1)


def one_card_per_language(entries, limit=1):
    """Whether a group of entries plausibly describes a single card.

    A printing must name one card in every language: a few sets number
    ambiguously — Japanese and Korean promos reuse 001 for unrelated cards — so
    such a group is not one card seen twice and must not be offered as another
    version of it.

    A fingerprint is structural, so cards that really are built alike share one.
    Unown A to Z carry the same Pokédex number, HP, retreat cost, illustrator and
    attack, and differ only by a letter in the name. A family like that shows up
    as one language contributing many names at once, while a translation or a
    spelling variant of a single card contributes two — so fingerprints tolerate
    a little disagreement where printings tolerate none.

    Both the index and the linking report read this, so what the viewer shows and
    what the report counts can never drift apart.
    """
    return names_per_language(entries) <= limit


def keys_for(card):
    """Both keys, skipping whichever the card cannot support."""
    found = {}
    for name, value in (("print_key", print_key(card)), ("card_key", card_key(card))):
        if value:
            found[name] = value
    return found
