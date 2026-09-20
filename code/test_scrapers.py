"""
Tests for the parts that have gone wrong before.

Every check here stands for a real defect that reached the stored cards, so
the suite is the cheapest way to keep them from coming back. It needs no
network and no test framework:

    uv run code/test_scrapers.py

September 16, 2026 by Weihang
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import bs4
from loguru import logger

import paths

FAILURES = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        FAILURES.append(name)


def sandbox():
    """Point every data folder at a throwaway directory.

    Every language, not just the five with a preset path: a language that
    falls through to the default would otherwise be written for real.
    """
    temp = Path(tempfile.mkdtemp())
    for lang in paths.LANGS:
        paths.DATA[lang] = temp / f"data_{lang}"
    return temp


def test_collector_numbers():
    from CardScraperTC import CardScraperTC

    scraper = CardScraperTC(locale="tw")
    check("collector 108/086", scraper.parse_collector("108/086"), ("108", "086"))
    # A card printed with two numbers keeps the pair that names it.
    check("collector two numbers", scraper.parse_collector("151/103,152/103"), ("151", "103"))
    # "n/a" must not be split into number "n" and total "a".
    check("collector n/a", scraper.parse_collector("n/a"), ("n/a", -1))
    check("collector bare code", scraper.parse_collector("SV-P"), ("SV-P", -1))


def test_set_name_is_case_sensitive():
    from CardScraperTC import CardScraperTC

    scraper = CardScraperTC(locale="tw")
    scraper._expansion_codes = sorted(
        ["SVF", "M6a", "SV7", "SV11W", "S10b", "SVM"], key=len, reverse=True
    )
    # A case-insensitive file system once made `svf` look like the folder
    # `SVF`, which stored the wrong capitalisation on every new card.
    (paths.data_dir("tc") / "SVF").mkdir(parents=True, exist_ok=True)
    check("symbol svf.png", scraper.format_set_name("svf.png"), "SVF")
    check("symbol tw_m6af_exp.png", scraper.format_set_name("tw_m6af_exp.png"), "M6a")
    check("symbol SV7_twhk_exp.png", scraper.format_set_name("SV7_twhk_exp.png"), "SV7")
    check("symbol S10bF @4x.png", scraper.format_set_name("S10bF @4x.png"), "S10b")


def test_korean_rule_is_not_an_attack():
    from Card import Card
    from CardScraperKO import CardScraperKO

    html = """
    <div class="pokemon-abilities">
      <div class="ability mgt0"><div class="area-parent">
        <h4 class="left label"><span class="skil_name">[찬란한 포켓몬 룰]</span></h4>
      </div><p>찬란한 포켓몬은 덱에 1장만 넣을 수 있다.</p></div>
      <div class="ability"><div class="area-parent">
        <img src="/symbol/type5.png" title="초"><img src="/symbol/type9.png" title="무색">
        <h4 class="left label"><span class="skil_name">마인드룰러</span> <span class="plus">20×</span></h4>
      </div><p>상대의 패의 장수 × 20데미지를 준다.</p></div>
    </div>"""
    card = Card()
    card.set_card_type("Pokémon")
    card.set_out_id("test")
    CardScraperKO().get_abilities_and_attacks(card, bs4.BeautifulSoup(html, "html.parser"))
    # 마인드룰러 contains the letters of "rule" but is an attack, not a rule.
    check("korean attack kept", [a["name"] for a in card.attacks], ["마인드룰러"])
    check("korean attack cost", card.attacks[0]["cost"], ["Psychic", "Colorless"])
    check("korean rule box", card.rule_box, "찬란한 포켓몬은 덱에 1장만 넣을 수 있다.")
    check("korean radiant tag", card.tags, ["찬란한"])


def test_pocket_effect_spacing():
    from CardScraperPocket import CardScraperPocket

    scraper = CardScraperPocket()
    # The page puts part of a sentence in its own element. Joining the parts
    # without a separator once stored "in play(both yours ...)gets".
    sentence = "Each Basic Pokémon in play (both yours and your opponent's) gets +20 HP."
    check("pocket keeps spacing", scraper.read_effect(sentence), sentence)
    check(
        "pocket energy letter",
        scraper.read_effect("Attach 1 [W] Energy."),
        "Attach 1 {Water} Energy.",
    )


def test_tcgdex_card_mapping():
    from CardScraperTCGdex import CardScraperTCGdex

    scraper = CardScraperTCGdex(lang="zh-cn")
    payload = {
        "name": "蓋蓋蟲",
        "category": "Pokemon",
        "localId": "007",
        "image": None,  # Simplified Chinese publishes no pictures
        "rarity": "None",  # the API's placeholder for "no rarity"
        "set": {"id": "SV9", "name": "對戰搭檔", "cardCount": {"total": 100}},
        "hp": 60,
        "types": ["Grass"],
        "stage": "Basic",
        "attacks": [{"cost": ["Colorless"], "name": "推倒", "damage": 10, "effect": "換手"}],
    }
    scraper.get_json = lambda url: payload  # no network in the tests
    path = paths.data_dir("sc") / "SV9" / "007.json"
    scraper.read_card("SV9-007")
    stored = json.loads(path.read_text(encoding="utf-8"))

    # "None" is a placeholder, not a rarity, and storing it reads as a bug.
    check("tcgdex drops the rarity placeholder", "rarity" in stored, False)
    check("tcgdex names its source", [s["name"] for s in stored["sources"]], ["TCGdex"])
    check("tcgdex keeps the attack", [a["name"] for a in stored["attacks"]], ["推倒"])
    check("tcgdex records the set total", stored["set_total"], 100)
    # Saving is what derives the linking keys. A scraper that wrote its cards
    # any other way would store none of them, and link to nothing.
    check("tcgdex derives a print key on save", bool(stored.get("print_key")), True)


def test_card_identity_keys():
    import cardkeys

    pikachu_jp = {
        "lang": "jp", "set_name": "M6a", "number": "018",
        "pokedex_number": 25, "hp": 70, "retreat": 1, "author": ["danciao"],
        "attacks": [{"cost": ["Lightning", "Colorless", "Colorless"],
                     "damage": {"amount": 80, "suffix": ""}}],
    }
    # Korea and Taiwan number a set exactly as Japan does, and Korea stores HP
    # as text where Japan stores a number — neither may break the match.
    pikachu_ko = dict(pikachu_jp, lang="ko", hp="70")
    check("print key crosses languages", cardkeys.print_key(pikachu_ko), cardkeys.print_key(pikachu_jp))
    check("card key survives a text HP", cardkeys.card_key(pikachu_ko), cardkeys.card_key(pikachu_jp))
    # The zeros carry nothing: one source writes 018 where another writes 18.
    check("print key value", cardkeys.print_key(pikachu_jp), "asia:M6a-18")

    # TCGdex numbers its own way, so its keys must not collide with Japan's.
    french = dict(pikachu_jp, lang="fr", set_name="sv01")
    check("families stay apart", cardkeys.print_key(french), "tcgdex:sv01-18")

    # A "number" that is not a number identifies nothing.
    check("set code as number", cardkeys.print_key({"lang": "jp", "set_name": "SV-P", "number": "SV-P"}), None)
    check("n/a as number", cardkeys.print_key({"lang": "tc", "set_name": "SVB", "number": "n/a"}), None)

    # A Trainer has no Pokédex number, HP or attacks to fingerprint.
    trainer = {"lang": "tc", "set_name": "M6a", "number": "103", "card_type": "物品卡"}
    check("trainer keyed by printing only", cardkeys.keys_for(trainer), {"print_key": "asia:M6a-103"})


def test_species_from_card_name():
    import cardkeys

    check("plain species", cardkeys.dex_from_name("Noctowl"), 164)
    check("owner prefix", cardkeys.dex_from_name("Iono’s Tadbulb"), 938)
    check("form and mechanic", cardkeys.dex_from_name("Mega Venusaur ex"), 3)
    check("regional form", cardkeys.dex_from_name("Alolan Persian"), 53)
    # A name it cannot place must return nothing rather than a wrong species.
    check("unplaceable name", cardkeys.dex_from_name("Buried Fossil"), None)

    # Japanese and Korean names run the species together with everything else,
    # so the species is found inside the name. The longest match wins, or
    # リザードン would be read as リザード.
    check("japanese owner name", cardkeys.dex_from_name("ナンジャモのズピカ", "jp"), 938)
    check("japanese mega and ex", cardkeys.dex_from_name("メガリザードンXex", "jp"), 6)
    check("korean name", cardkeys.dex_from_name("피카츄", "ko"), 25)
    # French wraps the owner after the species: "Têtampoule de Mashynn".
    check("french owner name", cardkeys.dex_from_name("Têtampoule de Mashynn", "fr"), 938)

    # English publishes no Pokédex number, so the name has to supply it — and
    # the result has to match what Japanese and French produce for that card.
    english = {
        "lang": "en", "set_name": "SVI", "number": "001", "name": "Noctowl",
        "hp": 100, "retreat": 1, "author": ["matazo"],
        "attacks": [{"cost": ["Colorless", "Colorless"], "damage": 60}],
    }
    japanese = dict(english, lang="jp", name="ヨルノズク", pokedex_number=164)
    check("english fingerprints", cardkeys.card_key(english), "164|100|1|matazo|60|2")
    check("and matches Japanese", cardkeys.card_key(japanese), cardkeys.card_key(english))

    # A Pokémon with no attack recorded is too thin to fingerprint safely.
    check("no attacks, no fingerprint", cardkeys.card_key(dict(english, attacks=[])), None)


def test_saving_a_card_twice():
    from Card import Card

    def build(url, name):
        card = Card()
        card.set_url(url)
        card.set_card_name(name)
        card.set_img("i")
        card.set_card_type("Pokémon")
        card.set_jp_id(1)
        card.set_set("TEST")
        card.set_collector("001", "100")
        return card

    first = build("http://x/1", "A").save()
    again = build("http://x/1", "A again").save()
    check("same card keeps one file", again, first)
    check("same card is updated", json.loads(again.read_text())["name"], "A again")

    # A different card that happens to share a number gets its own file.
    other = build("http://x/2", "B")
    other.set_jp_id(2)
    check("different card, own file", other.save().name, "2.json")

    # A field an earlier scrape stored is never dropped by a later one.
    stored = json.loads(first.read_text())
    stored["kept_field"] = "keep me"
    first.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
    merged = json.loads(build("http://x/1", "A third").save().read_text())
    check("earlier field kept", merged.get("kept_field"), "keep me")
    check("new value wins", merged["name"], "A third")

    # ...but a field the normalisation removes must not come back through the
    # merge, or an earlier run's mistake would outlive every correction.
    polluted = json.loads(first.read_text())
    polluted["rule_box"] = "copied out of the attack"
    first.write_text(json.dumps(polluted, ensure_ascii=False), encoding="utf-8")
    fourth = build("http://x/1", "A fourth")
    fourth.add_attack(["Colorless"], "Hit", "10", "copied out of the attack")
    rewritten = json.loads(fourth.save().read_text())
    check("merge does not resurrect a dropped rule box", "rule_box" in rewritten, False)
    check("the attack survives the merge", rewritten["attacks"][0]["effect"], "copied out of the attack")


def test_card_without_a_number():
    from Card import Card

    card = Card()
    card.set_url("http://x/9")
    card.set_card_name("no number")
    card.set_img("i")
    card.set_card_type("Pokémon")
    card.set_lang("ko")
    card.set_out_id("BS123")
    card.set_set("M5")
    # A page that states no collector number must still save.
    check("card with no number", card.save().name, "BS123.json")


def test_misfiled_fields_are_corrected():
    """A rule is not an attack, and a rule box is never an attack's effect."""
    from Card import Card

    empty_block = {
        "name": "櫻花寶",
        "attacks": [
            {"name": "樹葉", "cost": ["Grass"], "damage": "10", "effect": ""},
            {"name": "", "cost": [], "damage": "", "effect": ""},
        ],
    }
    Card.normalize_fields(empty_block)
    check("unnamed block is not an attack", [a["name"] for a in empty_block["attacks"]], ["樹葉"])

    trainer_rule = {
        "name": "勝利之證(亞軍)",
        "effect": "擲1次硬幣若為正面，則從自己的牌庫選擇1張寶可夢卡。",
        "attacks": [
            {"name": "", "cost": [], "damage": "", "effect": "在自己的回合時，物品卡可不限張數使用。"},
            {"name": "", "cost": [], "damage": "", "effect": ""},
        ],
    }
    Card.normalize_fields(trainer_rule)
    check("unnamed rule becomes the rule box", trainer_rule["rule_box"], "在自己的回合時，物品卡可不限張數使用。")
    check("unnamed rule leaves no attack behind", "attacks" in trainer_rule, False)

    tagged = {
        "name": "뮤츠 EX",
        "tags": ["포켓몬 EX", "EX"],
        "rule_box": "포켓몬 EX가 기절한 경우 상대는 프라이즈를 2장 가져간다.",
        "attacks": [
            {
                "name": "사이코번",
                "cost": ["Psychic"],
                "damage": "120",
                "effect": "포켓몬 EX가 기절한 경우 상대는 프라이즈를 2장 가져간다.",
            }
        ],
    }
    Card.normalize_fields(tagged)
    check("rule text leaves the attack", tagged["attacks"][0]["effect"], None)
    check("a tagged card keeps its rule box", bool(tagged.get("rule_box")), True)

    untagged = {
        "name": "샹델라",
        "rule_box": "상대의 패의 장수 × 30데미지를 준다.",
        "attacks": [
            {
                "name": "마인드룰러",
                "cost": ["Psychic"],
                "damage": "30×",
                "effect": "상대의 패의 장수 × 30데미지를 준다.",
            }
        ],
    }
    Card.normalize_fields(untagged)
    check("an untagged card drops the copied rule box", "rule_box" in untagged, False)
    check("the attack keeps its own effect", untagged["attacks"][0]["effect"], "상대의 패의 장수 × 30데미지를 준다.")


def test_types_are_named_in_english():
    """The type table is read out of the links, and never guessed.

    A name no link can place stays unplaced: a card keeps what it prints, and
    gains no English name at all, rather than one invented for it.
    """
    import canonicalTypes

    table = {("de", "Feuer"): "Fire", ("de", "Pflanze"): "Grass"}
    check("a placed name is translated", canonicalTypes.english_types("de", ["Feuer"], table), ["Fire"])
    check(
        "an English source is left as printed",
        canonicalTypes.english_types("en", ["Lightning"], table),
        ["Lightning"],
    )
    check("an unplaced name is not guessed", canonicalTypes.english_types("de", ["Fee"], table), None)
    check(
        "both types of a dual card are named",
        canonicalTypes.english_types("de", ["Feuer", "Pflanze"], table),
        ["Fire", "Grass"],
    )


def test_types_are_searchable_in_both_languages():
    """A type can be searched as printed and in English, and never twice."""
    import buildIndex

    german = {"name": "Tannza", "types": ["Pflanze"], "types_en": ["Grass"], "effect": ""}
    text = buildIndex.text_of(german)
    check("the printed type is searchable", "Pflanze" in text, True)
    check("the English type is searchable", "Grass" in text, True)

    english = {"name": "Pineco", "types": ["Grass"], "types_en": ["Grass"]}
    check("an English card does not repeat itself", buildIndex.text_of(english).count("Grass"), 1)


def test_species_names_survive_character_width():
    """A name written half-width must find a table spelled full-width.

    The species table holds ポリゴン２ and ポリゴンｚ; the cards print ポリゴン2 and
    ポリゴンZ. Unfolded, neither matches and the only name that does is ポリゴン —
    a different Pokémon, three evolutions earlier.
    """
    import cardkeys

    check("ポリゴン2 is Porygon2", cardkeys.dex_from_name("ポリゴン2", "jp"), 233)
    check("ポリゴンZ is Porygon-Z", cardkeys.dex_from_name("ポリゴンZ", "jp"), 474)
    check("ポリゴン is still Porygon", cardkeys.dex_from_name("ポリゴン", "jp"), 137)
    check("a mega form still reads its species", cardkeys.dex_from_name("メガリザードンX", "jp"), 6)

    # English names are spelled as PokéAPI spells them: no apostrophe, no dot,
    # and the gender as a letter.
    check("Farfetch'd", cardkeys.dex_from_name("Farfetch’d", "en"), 83)
    check("Mr. Mime", cardkeys.dex_from_name("Mr. Mime", "en"), 122)
    check("Nidoran Female", cardkeys.dex_from_name("Nidoran Female", "en"), 29)
    check("Nidoran Male", cardkeys.dex_from_name("Nidoran Male", "en"), 32)
    check("Mime Jr. still resolves", cardkeys.dex_from_name("Mime Jr.", "en"), 439)


def test_species_is_read_through_the_words_around_it():
    """A card name wraps its species in words no species table holds.

    Every one of these went unplaced, and a card with no Pokédex number gets no
    fingerprint, so it reached no other language: 278 English cards, 170 French,
    30 German, 20 Italian and 15 Spanish. The species is now looked for in each
    run of neighbouring words, longest first, which is why the whole name still
    wins over either half of it.
    """
    import cardkeys

    # The form and nickname prefixes the game prints in front of a species.
    check("M Charizard EX is Charizard", cardkeys.dex_from_name("M Charizard EX", "en"), 6)
    check("Dusk Mane Necrozma", cardkeys.dex_from_name("Dusk Mane Necrozma GX", "en"), 800)
    check("Origin Forme Palkia", cardkeys.dex_from_name("Origin Forme Palkia VSTAR", "en"), 484)
    check("Teal Mask Ogerpon", cardkeys.dex_from_name("Teal Mask Ogerpon ex", "en"), 1017)
    check("Special Delivery Charizard", cardkeys.dex_from_name("Special Delivery Charizard", "en"), 6)
    check("Snow-cloud Castform", cardkeys.dex_from_name("Snow-cloud Castform", "en"), 351)

    # A two-word species still beats either of its words.
    check("Mr. Mime E4 is Mr. Mime", cardkeys.dex_from_name("Mr. Mime E4", "en"), 122)
    check("Tapu Koko Prism Star", cardkeys.dex_from_name("Tapu Koko Prism Star", "en"), 785)
    check("Type: Null", cardkeys.dex_from_name("Type: Null", "en"), 772)

    # Porygon-Z was read as Porygon, three evolutions earlier.
    check("Porygon-Z is not Porygon", cardkeys.dex_from_name("Porygon-Z LV.X", "en"), 474)

    # A card naming several Pokémon names the first of them. The comma is not
    # part of a name, and leaving it attached handed the card to the second.
    check("Arceus, Dialga et Palkia", cardkeys.dex_from_name("Arceus, Dialga et Palkia GX", "fr"), 493)
    check("Sulfura is Moltres", cardkeys.dex_from_name("Sulfura, Électhor et Artikodin-GX", "fr"), 146)
    check("Pikachu & Zekrom names Pikachu", cardkeys.dex_from_name("Pikachu & Zekrom-GX", "en"), 25)

    # The sources disagree with their own tables about accents and apostrophes.
    check("Evoli unaccented is Évoli", cardkeys.dex_from_name("Evoli", "fr"), 133)
    check("Évoli accented still reads", cardkeys.dex_from_name("Évoli", "fr"), 133)
    check("Morpheo is Castform", cardkeys.dex_from_name("Morpheo Soleil", "fr"), 351)
    check("straight apostrophe reads", cardkeys.dex_from_name("Farfetch'd", "it"), 83)
    check("curly apostrophe still reads", cardkeys.dex_from_name("Sirfetch’d di Galar", "it"), 865)

    # Japanese marks its kana with a dakuten, which is not an accent: dropping it
    # turns Marowak into Cubone, so that table is never folded.
    check("ガラガラ is Marowak", cardkeys.dex_from_name("ガラガラ", "jp"), 105)
    check("カラカラ is Cubone", cardkeys.dex_from_name("カラカラ", "jp"), 104)

    # Nidoran's name ends in a symbol, written every way the sources can.
    check("Nidoran ♂", cardkeys.dex_from_name("Nidoran ♂", "fr"), 32)
    check("Nidoran ♀", cardkeys.dex_from_name("Nidoran ♀", "fr"), 29)
    check("German Nidoran M", cardkeys.dex_from_name("Nidoran M", "de"), 32)
    check("German Nidoran W", cardkeys.dex_from_name("Nidoran W", "de"), 29)
    check("a delta species keeps its gender", cardkeys.dex_from_name("Nidoran M δ", "de"), 32)
    # PokéAPI's own table spells them `nidoran-m` and `nidoran-f`. Reading that
    # final letter as the gender rewrote a name that already matched, and cost
    # 16 English cards their number.
    check("Nidoran Male keeps its own spelling", cardkeys.dex_from_name("Nidoran Male", "en"), 32)
    check("Nidoran Female keeps its own spelling", cardkeys.dex_from_name("Nidoran Female", "en"), 29)

    # A card that names no Pokémon is left unplaced rather than guessed at.
    check("Buried Fossil names nothing", cardkeys.dex_from_name("Buried Fossil", "en"), None)


def test_a_stated_dex_number_is_read_as_a_number():
    """A fingerprint is text, so `No.491` and `491` were two different cards.

    Ten Japanese pages print the number that way. Reading the digits out of it
    put seven of those cards back with their other printings, two of them
    reaching nine languages. `-1` and `0` are how a source says it states no
    number at all, and a card fingerprinted `-1|...` or `0|...` is not a Pokémon.
    """
    import cardkeys

    check("No.491 is 491", cardkeys.stated_dex("No.491"), 491)
    check("leading zeros go too", cardkeys.stated_dex("No.025"), 25)
    check("a plain string is a number", cardkeys.stated_dex("658"), 658)
    check("a number stays itself", cardkeys.stated_dex(658), 658)
    check("-1 states no number", cardkeys.stated_dex(-1), None)
    check("-1 written out states no number", cardkeys.stated_dex("-1"), None)
    check("0 states no number", cardkeys.stated_dex(0), None)
    check("nothing states no number", cardkeys.stated_dex(None), None)

    # The sentinel must leave the card unfingerprinted, not fingerprint it as
    # Bulbasaur, which is what reading `-1` as 1 would do.
    sentinel = {
        "pokedex_number": -1,
        "name": "ココ",
        "hp": 90,
        "retreat": 1,
        "author": "Tetsuo Yajima",
        "attacks": [{"damage": "120", "cost": ["G"]}],
        "lang": "jp",
    }
    check("a -1 card gets no fingerprint", cardkeys.card_key(sentinel), None)


def test_a_card_never_names_a_folder_below_its_own():
    """A field that names a file can hold anything the page printed.

    One Taiwanese promo stated its number as `039/M-P`. The separator placed the
    card a directory below the one that had just been made, the write failed, and
    nine cards were lost while the run reported them downloaded.
    """
    from Card import one_segment

    check("a slashed number is one segment", one_segment("039/M-P.json"), "039-M-P.json")
    check("a backslash too", one_segment("039\\M-P.json"), "039-M-P.json")
    check("an ordinary name is untouched", one_segment("021.json"), "021.json")
    check("an empty field still names something", one_segment("   "), "no_set")


def test_chinese_and_taiwanese_cards_reach_japan():
    """Simplified Chinese numbers as Japan does, and Taiwan respells a few sets.

    The marks matter as much as the codes: TCGdex writes `120+` where Japan
    writes `120＋`, and a fingerprint that keeps those apart splits one card into
    two. All three were measured before being relied on — 541 Simplified Chinese
    positions and 469 Taiwanese ones are the same Pokémon, none a different one.
    """
    import cardkeys

    japanese = {
        "lang": "jp", "set_code": "SV10", "number": "027", "name": "ユキノオー",
        "pokedex_number": 460, "hp": 150, "retreat": 4, "author": ["kamonabe"],
        "attacks": [
            {"damage": "90", "cost": ["Water", "Water", "Colorless"]},
            {"damage": "120＋", "cost": ["Water", "Water", "Colorless", "Colorless"]},
        ],
    }
    chinese = dict(
        japanese, lang="sc", name="暴雪王", number="27",
        attacks=[
            {"damage": "90", "cost": ["Water", "Water", "Colorless"]},
            {"damage": "120+", "cost": ["Water", "Water", "Colorless", "Colorless"]},
        ],
    )
    check("the printing is Asia's", cardkeys.print_key(japanese), "asia:SV10-27")
    check("simplified chinese keys as Japan", cardkeys.print_key(chinese), cardkeys.print_key(japanese))
    check("a full-width plus is the same mark", cardkeys.card_key(chinese), cardkeys.card_key(japanese))

    taiwanese = dict(japanese, lang="tc", set_code="SV2a F", number="165")
    tokyo = dict(japanese, set_code="SV2a", number="165")
    check("Taiwan's respelled set is Japan's", cardkeys.print_key(taiwanese), cardkeys.print_key(tokyo))
    check("a set genuinely called SVF is left alone",
          cardkeys.print_key(dict(japanese, set_code="SVF", number="1")), "asia:SVF-1")


def test_pocket_cards_link_across_languages():
    """One Pocket card is one printing, whichever language publishes it.

    TCGdex serves Pocket sets under its own languages with the same set ids, so
    the only thing standing between them was the leading zeros one side writes.
    English's Base Set 2 is "B2" and must not be mistaken for a Pocket set.
    """
    import cardkeys

    english = {"game": "TCG Pocket", "set_code": "A1", "number": "1", "name": "Bulbasaur"}
    french = {"lang": "fr", "set_code": "A1", "number": "001", "name": "Bulbizarre"}
    check("a Pocket card keys the same in both", cardkeys.print_key(french), cardkeys.print_key(english))
    check("pocket key value", cardkeys.print_key(english), "pocket:A1-1")

    base_set_two = {"lang": "en", "set_code": "B2", "number": "10", "name": "Blastoise"}
    check("Base Set 2 is not a Pocket set", cardkeys.print_key(base_set_two), "en:B2-10")

    german = {"lang": "de", "set_code": "swsh1", "number": "007", "name": "Glumanda"}
    check("a main-series number loses its zeros too", cardkeys.print_key(german), "tcgdex:swsh1-7")


def test_ambiguous_printings_do_not_link():
    """A promo number that several different cards share is not a version of any.

    Japanese and Korean promo sets reuse 001, so `promo 001` names no single
    printing. Punctuation, though, is not a different card: Traditional Chinese
    stores one name both with and without its angle brackets.
    """
    import buildIndex

    one_card = [
        ["jp", "ナンジャモのズピカ", "MC", "273", None],
        ["tc", "<奇樹的>光蚪仔", "MC", "273", None],
        ["tc", "奇樹的光蚪仔", "MC", "273", None],
    ]
    different_cards = [
        ["jp", "ミュウツー", "MG", "001", None],
        ["jp", "モンジャラ", "MG", "001", None],
    ]
    check("punctuation is not another card", buildIndex.one_card_per_language(one_card), True)
    check("a reused promo number links to nothing", buildIndex.one_card_per_language(different_cards), False)

    # A fingerprint is structural, so a whole family can share one: Unown A to Z
    # differ by a letter and nothing else. A spelling variant of one card is not
    # that, so fingerprints allow two names in a language and printings allow one.
    look_alikes = [["en", f"Unown {letter}", "N4", "57", None] for letter in "ABCDE"]
    check("look-alike cards share no fingerprint", buildIndex.one_card_per_language(look_alikes, 2), False)

    spelling_variant = [
        ["fr", "Carchacrock-ex de Cynthia", "sv6a", "112", None],
        ["fr", "Carchacrok-ex de Cynthia", "sv6a", "112", None],
        ["jp", "シロナのガブリアスex", "SV6a", "112", None],
    ]
    check("a spelling variant is still one card", buildIndex.one_card_per_language(spelling_variant, 2), True)


def test_image_archive_layout():
    """Where a picture is written, and where a viewer looks for it, must agree.

    The viewers build a picture's address from the language, the set name and
    the card's file name. If the downloader ever wrote them anywhere else, both
    viewers would quietly show nothing.
    """
    import downloadImages

    check("archive is not inside the repository", paths.ROOT in downloadImages.DEFAULT_DIR.parents, False)
    check("archive sits beside the repository", downloadImages.DEFAULT_DIR.parent, paths.ROOT.parent)

    folder = paths.data_dir("jp") / "M6a"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "31651.json").write_text(
        json.dumps({"img": "https://example.com/card/31651.png"}), encoding="utf-8"
    )
    targets = downloadImages.image_targets("jp", Path("/tmp/archive"))
    check(
        "picture lands under lang/set/file",
        Path("/tmp/archive/jp/M6a/31651.png") in targets,
        True,
    )


def test_rule_box_tags():
    from Card import Card

    def tags_for(rule):
        card = Card()
        card.set_card_type("Pokémon")
        card.set_out_id("t")
        card.set_rule_box(rule)
        return card.tags

    # A Mega Evolution ex is both, and carries both tags.
    check("mega evolution (en)", tags_for("Mega Evolution ex rule: ..."), ["ex", "Mega Evolution"])
    check("mega evolution (jp)", tags_for("メガシンカexがきぜつしたとき、相手はサイドを3枚とる。"), ["ex", "メガシンカ"])
    check("radiant (ko)", tags_for("찬란한 포켓몬은 덱에 1장만 넣을 수 있다."), ["찬란한"])


def main():
    logger.remove()
    temp = sandbox()
    try:
        for test in (
            test_collector_numbers,
            test_set_name_is_case_sensitive,
            test_korean_rule_is_not_an_attack,
            test_pocket_effect_spacing,
            test_tcgdex_card_mapping,
            test_card_identity_keys,
            test_species_from_card_name,
            test_saving_a_card_twice,
            test_card_without_a_number,
            test_rule_box_tags,
            test_misfiled_fields_are_corrected,
            test_types_are_named_in_english,
            test_types_are_searchable_in_both_languages,
            test_species_names_survive_character_width,
            test_species_is_read_through_the_words_around_it,
            test_a_stated_dex_number_is_read_as_a_number,
            test_a_card_never_names_a_folder_below_its_own,
            test_chinese_and_taiwanese_cards_reach_japan,
            test_pocket_cards_link_across_languages,
            test_ambiguous_printings_do_not_link,
            test_image_archive_layout,
        ):
            print(test.__name__)
            test()
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
