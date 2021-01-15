import bs4
import sys
import requests
import re
import json


def readCharacter(chaId):
    # anti-scraping
    user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"
    url = f'https://op.mobage.cn/wiki/role/{chaId}'
    response = requests.get(url, headers={'User-Agent': user_agent})
    if response.status_code == 200:
        # print(response.content.decode('utf-8'))
        content = response.content.decode('utf-8')
    else:
        # print(f"Fail to get the url [{chaId}, {response.status_code}]")
        return

    # start reading content
    soup = bs4.BeautifulSoup(content, 'html.parser')

    # save all data in a json node
    node = {}

    ## role-bg
    name = soup.find('img', id='li_hui')['alt']
    img = soup.find('img', id='li_hui')['src'].split('img/')[1]
    rating = soup.find('div', class_='img-attr').attrs['class'][1]
    tags = soup.find('div', class_='role-tags').get_text(' ').split()
    show = soup.find('p', class_='role-show').get_text()
    roleEquip = soup.find('p', class_='role-equip').get_text(' ').split()[1]
    way = soup.find('p', class_='role-way').get_text(' ').split()[1]

    node = {
        '人物': name,
        '立绘': img,
        '头像': None,
        '级别': rating,
        '标签': tags,
        '图鉴': show,
        '专属': {
            roleEquip: None,},
        '获取途径': way}
    
    if rating == 'c':
        return node

    # optional parts: tupo, skin
    tupo = soup.find('li', class_='tupo-bg')
    if tupo:
        if tupo.find('a'):
            tupoId = int(tupo.find('a')['href'].split('/')[-1])
        else:
            tupoId = None
    else:
        # no tupo
        tupoId = None
    node['突破人物'] = tupoId

    skins = []
    for skin in soup.findAll('li', class_='skin-bg'):
        skins.append(skin['data-img'].split('img/')[1])
    node['皮肤'] = skins

    ## part-1
    attrs = soup.find('ul', class_='clear').get_text(' ').split()
    attrNames = [s.replace('：','').strip() for s in attrs[0::2]]
    attrValues = [float(s) for s in attrs[1::2]]
    attrDict = {}
    for i in range(len(attrNames)):
        attrDict[attrNames[i]] = attrValues[i]
    node['属性'] = attrDict

    # skill
    base = soup.find('div', class_='base-skill')
    skillImgs = [u.attrs['style'].split('img/')[1][:-1]
                 for u in base.findAll('span')[1:]]
    skillList = [p.get_text() for p in base.findAll('p')]
    skillNames = skillList[0::2]
    skillDesc = skillList[1::2]
    skillDict = {}
    for i in range(min(len(skillImgs), len(skillNames))):
        skillDict[skillNames[i]] = {"desc": skillDesc[i], "img": skillImgs[i]}
    node['技能'] = skillDict

    team = soup.find('div', class_='base-team')
    teamCount = len(team.findAll('span', class_='title-span'))
    teamP = team.findAll('p')
    if teamCount == 2:
        # team, gem
        teamList = [p.get_text() for p in teamP[:5]]
        teamP = teamP[5:]
        node['阵容方案'] = teamList
    elif teamCount != 1:
        raise ValueError("Unknown Team Description")

    # gem
    gems = [p.get_text() for p in teamP]
    node['共鸣方案'] = gems

    # equip
    equipDict = {}
    for equip in soup.findAll('div', class_='equip-part'):
        equipText = equip.get_text(' ').split()
        add = {}
        for e in equipText[1:]:
            string = e.split('+')
            add[string[0]] = int(string[1])
        equipDict[equipText[0]] = add
    node['装备'] = equipDict

    roleEquipImg = soup.findAll('span', class_='equip')[4].attrs['style'].split('img/')[1][:-1]
    node['专属'][roleEquip] = roleEquipImg

    jxxg = soup.find('div', class_='taps-jxxg')
    jxxgDict = {}
    jxLevel = jxxg.find('div', class_='child-tap').get_text(" ").split()
    jxAddText = jxxg.findAll('div', class_='add-value')
    jxEffectText = jxxg.findAll('div', class_='flex-part')
    jxEffect = [flex.find('p').get_text() for flex in jxEffectText][1::3]
    for level in range(len(jxLevel)):
        jxAdd = {}
        for i in jxAddText[level].get_text(' ').split()[1:]:
            string = i.split('：')
            jxAdd[string[0]] = int(string[1])
        jxxgDict[jxLevel[level]] = {"成长值": jxAdd, "效果": jxEffect[level]}
    node['觉醒'] = jxxgDict

    avatar = jxxg.findAll('div', class_='avatar-bg')[1].find('img')['src'].split('img/')[1]
    node['头像'] = avatar

    doctor = soup.find('div', class_='taps-chuanyi').find('p').get_text().split('+')
    node['船医'] = {doctor[0]: doctor[1]}
    
    # optional: chufang, zszb, jiban, tupo
    kitchen = soup.find('div', class_='taps-chufang')
    if kitchen:
        kitchen = kitchen.find('div', class_='add-value').get_text(' ').split()[1::2]
        kitchenDict = {}
        for k in kitchen:
            ks = k.split(':')
            kitchenDict[ks[0]] = ks[1]
        node['厨房'] = kitchenDict

    zszb = soup.find('div', class_='taps-zszb')
    if zszb:
        zszb = zszb.get_text(' ').split()
        node[zszb[-2].split('：')[0]] = zszb[-1]

    jiban = soup.find('div', class_='taps-jiban')
    if jiban:
        jibanDict = {}
        jibanCount = jiban.find('ul').get_text(' ').split()
        jibans = jiban.findAll('div', class_='part')
        for i in range(len(jibanCount)):
            jDict = {}
            j = jibans[i].get_text(' ').split()
            jDict[j[1]] = j[2]
            people = [txt.split("觉醒")[0] for txt in j[4:-2]]
            jDict["升级条件"] = people
            jibanDict[jibanCount[i]] = jDict
        node['羁绊'] = jibanDict

    tupo = soup.find('div', class_='taps-tupo')
    if tupo:
        tupoDict = {}
        taskList = tupo.findAll('div', class_='desc-part')
        if taskList[0].get_text():
            task = [t.get_text(' ').split()[0] for t in taskList]
            tupoDict["突破任务"] = task
        tupoAdd = tupo.findAll('div', class_='w170')[1].get_text(' ').split()[1:]
        tupoAddDict = {}
        for li in [re.split(r'(\d+)', l) for l in tupoAdd]:
            tupoAddDict[li[0]] = int(li[1])
        tupoDict["突破效果LV.60"] = tupoAddDict
        tupoSkill = [s.split('：')[1] 
                 for s in tupo.find('div', class_='right-top').get_text(' ').split()]
        tupoDict[tupoSkill[0]] = tupoSkill[1]
        node['突破'] = tupoDict

    ## optional: gonglue
    gonglue = soup.find('h2', class_='gonglue')
    if gonglue:
        glDict = {}
        gl = gonglue.nextSibling
        titles = gl.findAll('span', class_='red')
        urls = gl.findAll('a')
        for i in range(len(titles)):
            glDict[titles[i].get_text()] = urls[i]['href']
        node['攻略'] = glDict
    
    return node

def scrape(start, end):
    allCha = {}
    filename = f"{start}-{end}.json"
    n = end - start+1
    for i in range(n):
        chaId = start + i
        node = readCharacter(chaId)
        allCha[chaId] = node
        
        j = (i + 1) / n
        sys.stdout.write('\r')
        # the exact output you're looking for:
        sys.stdout.write("[%-20s] %d%%" % ('='*int(20*j), 100*j))
        sys.stdout.write(f"\t({i+1}/{n})")
        sys.stdout.flush()
        
    with open(filename, 'w', encoding='utf8') as f:
        f.write(json.dumps(allCha, sort_keys=False, indent=4, ensure_ascii=False))
        