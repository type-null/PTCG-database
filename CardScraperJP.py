"""
Scrape card info from pokemon-card.com
and save as csv file

author: type-null
date: July 2020
"""

import bs4
import requests

def getContent(url):
    # anti-scraping
    user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"
    
    response = requests.get(url, headers={'User-Agent': user_agent})
    if response.status_code == 200:
        # print(response.content.decode('utf-8'))
        return response.content
    else:
        print(f"Fail to get the url [{response.status_code}]")


def readPokemon(content):
    soup = bs4.BeautifulSoup(content, 'html.parser')
    card = soup.section
    # all type cards
    name = card.h1.get_text()

    # pokemon
    ## left box
    img = card.find('img', class_='fit')['src']

    reg = card.find('img', class_='img-regulation')['alt'] # regulation
    regImg = card.find('img', class_='img-regulation')['src']

    setNum = card.find('div', class_='subtext').get_text().strip()
    setCount = int(setNum.strip()[-3:])
    setNum = int(setNum.strip()[:3])

    if card.find('img', width='24'):
        rarityImg = card.find('img', width='24')['src']
        rarity = rarityImg.split('.')[0].split('rare_')[1]
    else:
        rarity = rarityImg = ''

    author = card.find('div', class_='author').get_text().strip().split('\n')[1]

    ### global pokedex
    pokedex = card.find('div', class_='card')
    if pokedex: # has pokedex
        [dexNum, dexClass] = pokedex.h4.get_text().strip().split('\u3000')
        dexNum = int(dexNum.split('.')[1])
        htAndWt = pokedex.p.get_text().split('：')
        height = float(htAndWt[1].split(' ')[0])
        weight = float(htAndWt[2].split(' ')[0])
        desc = pokedex.find_all('p')[1].get_text()
    else:
        [dexNum, dexClass, height, weight, desc] = [''] * 5

    ## right box
    stage = card.find('span', class_='type').get_text()
    if '\xa0' in stage:
        stage = stage.replace('\xa0', ' ')
    hp = card.find('span', class_='hp-num').get_text()
    hp = int(hp)
    pType = card.find('div', class_='td-r').find_all('span')[-1]['class'][0].split('-')[1]

    ### waza part
    part = content.split('<span class="hp-type">タイプ</span>')[1].split('</table>')[0].strip()
    soup = bs4.BeautifulSoup(part)
    wazaPart = bs4.BeautifulSoup(soup.prettify(formatter="minimal"))

    h2 = wazaPart.find_all('h2')
    skills = wazaPart.find_all('h4')
    p = wazaPart.find_all('p')
    # init
    [ability, abilityDesc, spRule] = [''] * 3
    for area in h2:
        areaType = area.get_text().strip()
        if areaType == "特性":
            # ability
            # print('learning an ability')
            ability = skills[0].get_text().strip()
            abilityDesc = p[0].get_text().strip()
            del skills[0]

        elif areaType == "特別なルール":
            # special rule
            # print('learning a special rule')
            spRule = p[-1].get_text().strip()
            del p[-1]
    # waza
    # init
    [waza1Cost, waza1Name, waza1Damage, waza1Desc] = [''] * 4
    [waza2Cost, waza2Name, waza2Damage, waza2Desc] = [''] * 4

    waza1Cost = [span['class'][0].split('-')[1] for span in skills[0].find_all('span', class_='icon')]
    waza1 = skills[0].get_text().strip().split(' ')
    waza1Name = waza1[0].strip()
    waza1Damage = waza1[-1]
    waza1Desc = skills[0].find_next_sibling('p').get_text().strip()

    if len(skills) > 1:
        waza2Cost = [span['class'][0].split('-')[1] for span in skills[1].find_all('span', class_='icon')]
        waza2 = skills[1].get_text().strip().split(' ')
        waza2Name = waza2[0].strip()
        waza2Damage = waza2[-1]
        waza2Desc = skills[1].find_next_sibling('p').get_text().strip()

    ### table
    [weakType, weakValue, resistType, resistValue] = [''] * 4
    td = wazaPart.find_all('td')
    if td[0].find('span'):
        weakType = td[0].find('span')['class'][0].split('-')[1]
        weakValue = td[0].get_text().strip()

    if td[1].find('span'):
        resistType = td[1].find('span')['class'][0].split('-')[1]
        resistValue = td[1].get_text().strip()

    escape = len(td[2].find_all('span'))


    return [name, img, reg, setNum, setCount, rarity, dexNum,
            dexClass, height, weight, desc, author, stage, hp, pType,
            ability, abilityDesc, waza1Cost, waza1Name, waza1Damage,
            waza1Desc, waza2Cost, waza2Name, waza2Damage, waza2Desc,
            weakType, weakValue, resistType, resistValue,
            escape, spRule]


