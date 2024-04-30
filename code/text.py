from bs4 import BeautifulSoup

html_content = """
<h2 class="mt20">ワザ</h2>
<h4>
    <span class="icon-none icon"></span>
    ユニオンゲイン&nbsp;
</h4>
<p>
    自分のトラッシュから
    <span class="icon-water icon"></span>
    エネルギーを2枚まで選び、このポケモンにつける。
</p>
<h4>
    <span class="icon-water icon"></span>
    アクアエッジ
    <span class="f_right Text-fjalla">130</span>
</h4>
<p></p>
<h4>
    <span class="icon-water icon"></span>
    <span class="icon-water icon"></span>
    <span class="icon-none icon"></span>
    たつまきしゅりけん&nbsp;
</h4>
<p>相手のベンチポケモン全員に、それぞれ100ダメージ。［ベンチは弱点・抵抗力を計算しない。］</p>
<h4>
    <span class="icon-water icon"></span>
    <span class="icon-water icon"></span>
    <span class="icon-none icon"></span>
    たきしばり
    <span class="f_right Text-fjalla">180</span>
</h4>
<p>次の相手の番、このワザを受けたポケモンは、にげられない。</p>
<h2 class="mt20">特性</h2>
<h4>しのびのからだ</h4>
<p>このポケモンは、相手が手札からグッズを出して使ったとき、その効果を受けない。</p>
<h2 class="mt20">特性</h2>
<h4>げどくじゅつ</h4>
"""


def my_func(h4, p):
    # Your processing logic here
    print("Heading:", h4.get_text(strip=True))
    print("Text:", p.get_text(strip=True))
    print()


soup = BeautifulSoup(html_content, "html.parser")

# Find all h2 tags
h2_tags = soup.find_all("h2")

for h2_tag in h2_tags:
    if h2_tag.get_text(strip=True) == "ワザ":
        next_h2 = h2_tag.find_next_sibling("h2")
        h4_tags = []
        sibling = h2_tag.find_next_sibling()
        while sibling and sibling != next_h2:
            if sibling.name == "h4":
                h4_tags.append(sibling)
            sibling = sibling.find_next_sibling()
        print(h4_tags)
