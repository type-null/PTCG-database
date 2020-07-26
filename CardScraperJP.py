"""
Scrape card info from pokemon-card.com
and save as csv file

author: type-null
date: July 2020
"""

import bs4
import sys
import requests
import pandas as pd


def getContent(cardId):
    # anti-scraping
    user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"
    url = f'https://www.pokemon-card.com/card-search/details.php/card/{cardId}'
    response = requests.get(url, headers={'User-Agent': user_agent})
    if response.status_code == 200:
        # print(response.content.decode('utf-8'))
        return response.content.decode('utf-8')
    else:
        print(f"Fail to get the url [{response.status_code}]")
        return [cardId, response.status_code]
    


def readEnergyMegaPrismstar(p):
    # <span class="pcg pcg-megamark"></span>
    # <span class="pcg pcg-prismstar">
    # <span class="icon-psychic icon">
    spans = p.find_all('span')
    marks = []
    if spans:
        for span in spans:
            if 'icon' in str(span):
                marks.append(span['class'][0].split('-')[1])
            elif 'mega' in str(span):
                marks.append(span['class'][1].split('-')[1][:4])
            elif 'prismstar' in str(span):
                marks.append(span['class'][1].split('-')[1])
        
        for i in range(len(marks)):
            p = str(p).replace(str(spans[i]), marks[i])
        p = bs4.BeautifulSoup(p)
    p = p.get_text().replace('\n   ', '')
    return p


def readCard(content):
    # start reading content
    soup = bs4.BeautifulSoup(content, 'html.parser')
    card = soup.section
    # all type cards
    name = readEnergyMegaPrismstar(card.h1)
    img = card.find('img', class_='fit')['src']
    
    # init
    [reg,         setNum,    setCount,   rarity,      dexNum,    dexClass,
     height,      weight,    dexDesc,    author,      desc,      stage, 
     hp,          pType,     ability,    abilityDesc, waza1Cost, waza1Name,
     waza1Damage, waza1Desc, waza2Cost,  waza2Name,   waza2Damage, waza2Desc,
     GXCost, GXName, GXDamage, GXDesc,
     weakType,    weakValue, resistType, resistValue, escape, spRule] = [''] * 34
    
    # decide card type
    cardType = card.h2.get_text()
    if cardType == '基本エネルギー':
        return [cardType, name, img, reg, setNum, setCount, rarity, dexNum,
            dexClass, height, weight, dexDesc, author, desc, stage, hp, pType,
            ability, abilityDesc, waza1Cost, waza1Name, waza1Damage,
            waza1Desc, waza2Cost, waza2Name, waza2Damage, waza2Desc,
            GXCost, GXName, GXDamage, GXDesc,
            weakType, weakValue, resistType, resistValue,
            escape, spRule]


    ## left box
    reg = card.find('img', class_='img-regulation')['alt'] # regulation
    regImg = card.find('img', class_='img-regulation')['src']
    
    setInfo = card.find('div', class_='subtext').get_text().strip()
    if len(setInfo.split('/')) == 2:
        setCount = setInfo.strip()[-3:]
        if setCount.isdigit():
            setCount = int(setCount)
        setNum = int(setInfo.strip()[:3])
    else:
        setCount = setInfo

    if card.find('img', width='24'):
        rarityImg = card.find('img', width='24')['src']
        rarity = rarityImg.split('.')[0].split('ic_')[1]
    
    if cardType == '特殊エネルギー':
        desc = readEnergyMegaPrismstar(card.find('p'))
        return [cardType, name, img, reg, setNum, setCount, rarity, dexNum,
            dexClass, height, weight, dexDesc, author, desc, stage, hp, pType,
            ability, abilityDesc, waza1Cost, waza1Name, waza1Damage,
            waza1Desc, waza2Cost, waza2Name, waza2Damage, waza2Desc,
                GXCost, GXName, GXDamage, GXDesc,
            weakType, weakValue, resistType, resistValue,
            escape, spRule]
    
    author = card.find('div', class_='author').get_text().strip()
    if author:
        author = card.find('div', class_='author').get_text().strip().split('\n')[1]

    ### national pokedex
    pokedex = card.find('div', class_='card')
    if pokedex: # has pokedex
        if pokedex.h4:
            dexline = pokedex.h4.get_text().strip().split('\u3000')
            if len(dexline) == 2:
                [dexNum, dexClass] = dexline
                dexNum = int(dexNum.split('.')[1])
            elif len(dexline) == 1:
                if any(char.isdigit() for char in dexline[0]):
                    dexNum = dexline[0]
                else:
                    dexClass = dexline[0]
        if len(pokedex.find_all('p')) == 2:
            htAndWt = pokedex.p.get_text().split('：')
            height = float(htAndWt[1].split(' ')[0])
            weight = float(htAndWt[2].split(' ')[0])
            dexDesc = pokedex.find_all('p')[1].get_text()
        elif len(pokedex.find_all('p')) == 1 and '重さ' in pokedex.find('p').get_text():
            htAndWt = pokedex.p.get_text().split('：')
            height = float(htAndWt[1].split(' ')[0])
            weight = float(htAndWt[2].split(' ')[0])
        elif len(pokedex.find_all('p')) == 1:
            dexDesc = pokedex.find('p').get_text()
    
    if cardType in ['サポート', 'グッズ', 'ポケモンのどうぐ', 'スタジアム']:
        desc = card.find_all('p')
        if cardType in ['サポート', 'グッズ', 'スタジアム']:
            desc = readEnergyMegaPrismstar(desc[0])
        if cardType == 'ポケモンのどうぐ':
            desc = readEnergyMegaPrismstar(desc[1])
        return [cardType, name, img, reg, setNum, setCount, rarity, dexNum,
            dexClass, height, weight, dexDesc, author, desc, stage, hp, pType,
            ability, abilityDesc, waza1Cost, waza1Name, waza1Damage,
            waza1Desc, waza2Cost, waza2Name, waza2Damage, waza2Desc,
                GXCost, GXName, GXDamage, GXDesc,
            weakType, weakValue, resistType, resistValue,
            escape, spRule]
    
    cardType = 'pokemon'

    ## right box
    stage = card.find('span', class_='type').get_text()
    if '\xa0' in stage:
        stage = stage.replace('\xa0', ' ')
    hp = card.find('span', class_='hp-num').get_text()
    hp = int(hp)
    topSpans = card.find('div', class_='td-r').find_all('span')
    topSpansClass = [span['class'] for span in topSpans]
    pTypes = [s for s in topSpansClass if 'icon' in s]
    pType = [l[0].split('-')[1] for l in pTypes]

    ### waza part
    part = content.split('<span class="hp-type">タイプ</span>')[1].split('</table>')[0].strip()
    soup = bs4.BeautifulSoup(part)
    wazaPart = bs4.BeautifulSoup(soup.prettify(formatter="minimal"))
    
    h2 = wazaPart.find_all('h2')
    skills = wazaPart.find_all('h4')
    if not skills[-1].get_text().strip():
        # empty (wrong special rule as void)
        del skills[-1]
    p = wazaPart.find_all('p')
    if not skills[0].get_text().strip():
        # mega evolution rule (delete)
        del skills[0]
        del p[0]
    
    for area in h2:
        areaType = area.get_text().strip()
        if areaType in ["特性", "古代能力"]:
            # ability or ancient trait
            # print('learning an ability')
            ability = skills[0].get_text().strip()
            abilityDesc = readEnergyMegaPrismstar(p[0]).strip()
            del skills[0]

        elif areaType == "特別なルール":
            # special rule
            # print('learning a special rule')
            spRule = readEnergyMegaPrismstar(p[-1]).strip()
            del p[-1]
            
        elif areaType == "GXワザ":
            # GX waza
            [GXCost, GXName, GXDamage, GXDesc] = [''] * 4
            # print('learning a GX attack')
            GXCost = [span['class'][0].split('-')[1] for span in skills[-1].find_all('span', class_='icon')]
            GX = skills[-1].get_text().strip().split(' ')
            GXName = GX[0].strip()
            GXDamage = GX[-1]
            if not GXDamage[-2].isdigit():
                GXDamage = ''
            GXDesc = skills[-1].find_next_sibling('p')
            GXDesc = readEnergyMegaPrismstar(GXDesc).strip()
            del skills[-1], p[-2]
            
        elif areaType == "ワザ":
            # waza
            waza1Cost = [span['class'][0].split('-')[1] for span in skills[0].find_all('span', class_='icon')]
            waza1 = skills[0].get_text().strip().split(' ')
            waza1Name = waza1[0].strip()
            waza1Damage = waza1[-1]
            if not waza1Damage[-2].isdigit():
                waza1Damage = ''
            waza1Desc = skills[0].find_next_sibling('p')
            waza1Desc = readEnergyMegaPrismstar(waza1Desc).strip()

            if len(skills) > 1:
                waza2Cost = [span['class'][0].split('-')[1] for span in skills[1].find_all('span', class_='icon')]
                waza2 = skills[1].get_text().strip().split(' ')
                waza2Name = waza2[0].strip()
                waza2Damage = waza2[-1]
                if not waza2Damage[-2].isdigit():
                    waza2Damage = ''
                waza2Desc = skills[1].find_next_sibling('p')
                waza2Desc = readEnergyMegaPrismstar(waza2Desc).strip()
                
        else:
            print(f"{name} has an unseen areaType: {areaType}!!")


    ### table
    td = wazaPart.find_all('td')
    if td[0].find('span'):
        weakType = td[0].find('span')['class'][0].split('-')[1]
        weakValue = td[0].get_text().strip()

    if td[1].find('span'):
        resistType = td[1].find('span')['class'][0].split('-')[1]
        resistValue = td[1].get_text().strip()

    escape = len(td[2].find_all('span'))
    

    return [cardType, name, img, reg, setNum, setCount, rarity, dexNum,
            dexClass, height, weight, dexDesc, author, desc, stage, hp, pType,
            ability, abilityDesc, waza1Cost, waza1Name, waza1Damage,
            waza1Desc, waza2Cost, waza2Name, waza2Damage, waza2Desc,
            GXCost, GXName, GXDamage, GXDesc,
            weakType, weakValue, resistType, resistValue,
            escape, spRule]


def scrapeCards(start, end):
    columns = ['cardId', 'cardType', 'name', 'img', 'regulation', 'setNum', 'setCount', 'rarity', 'dexNum',
                'dexClass', 'height', 'weight', 'dexDesc', 'author', 'desc', 'stage', 'hp', 'pType',
                'ability', 'abilityDesc', 'waza1Cost', 'waza1Name', 'waza1Damage',
                'waza1Desc', 'waza2Cost', 'waza2Name', 'waza2Damage', 'waza2Desc',
                'GXCost', 'GXName', 'GXDamage', 'GXDesc',
                'weakType', 'weakValue', 'resistType', 'resistValue', 'escape', 'spRule']

    cardDF = pd.DataFrame(columns=columns)
    errorDF = pd.DataFrame(columns=['errorCardId'])
    
    n = end - start+1
    for i in range(n):
        cardId = start + i
        content = getContent(cardId)
        soup = bs4.BeautifulSoup(content, 'html.parser')
        if soup.section:
            cardDF.loc[i] = [cardId] + readCard(content)
        else:
            errorDF.loc[i] = [cardId]
#         print(cardId)
        j = (i + 1) / n
        sys.stdout.write('\r')
        # the exact output you're looking for:
        sys.stdout.write("[%-20s] %d%%" % ('='*int(20*j), 100*j))
        sys.stdout.write(f"\t({i+1}/{n})")
        sys.stdout.flush()

    cardDF.reset_index().to_csv(f'output/cards_jp_{start}_{end}.csv')
    if len(errorDF) > 0:
        errorDF.reset_index().to_csv(f'output/error_id_{start}_{end}.csv')