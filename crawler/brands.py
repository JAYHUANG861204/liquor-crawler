"""品牌名稱統一成英文。

網站上的品牌寫法很亂（中文、中英混寫、全大寫），這裡統一轉成英文，
讓網頁上的「品牌」下拉選單可以跨網站比價。
找不到對照時保留原文；新的對照直接加進 ZH_EN 就好。
"""
from __future__ import annotations

import re

# 中文品牌 → 英文品牌（長的寫前面，比對時會先比長的）
ZH_EN = {
    "約翰走路": "Johnnie Walker", "起瓦士": "Chivas Regal", "皇家禮炮": "Royal Salute",
    "麥卡倫": "The Macallan", "格蘭利威": "The Glenlivet", "格蘭菲迪": "Glenfiddich",
    "百富": "The Balvenie", "格蘭傑": "Glenmorangie", "格蘭多納": "Glendronach",
    "波摩": "Bowmore", "拉弗格": "Laphroaig", "樂加維林": "Lagavulin", "雅柏": "Ardbeg",
    "大摩": "The Dalmore", "蘇格登": "Singleton", "泰斯卡": "Talisker", "布萊迪": "Bruichladdich",
    "格蘭冠": "Glen Grant", "坎貝爾": "Campbeltown", "亞伯樂": "Aberlour", "慕赫": "Mortlach",
    "布坎南": "Buchanan's", "百齡罈": "Ballantine's", "三隻猴子": "Monkey Shoulder",
    "噶瑪蘭": "Kavalan", "金車": "Kavalan", "響": "Hibiki", "山崎": "Yamazaki", "白州": "Hakushu",
    "余市": "Nikka", "宮城峽": "Nikka", "一甲": "Nikka", "竹鶴": "Nikka", "明石": "Akashi",
    "三得利": "Suntory", "知多": "Suntory",
    "傑克丹尼": "Jack Daniel's", "野火雞": "Wild Turkey", "美格": "Maker's Mark",
    "金賓": "Jim Beam", "尊美醇": "Jameson", "亡命之兔": "Dead Rabbit",
    "軒尼詩": "Hennessy", "馬爹利": "Martell", "人頭馬": "Rémy Martin", "拿破崙": "Courvoisier",
    "柑曼怡": "Grand Marnier", "君度": "Cointreau", "百利": "Baileys", "班尼迪克丁": "Benedictine",
    "坦奎利": "Tanqueray", "高登": "Gordon's", "亨利爵士": "Hendrick's", "孟買藍鑽": "Bombay Sapphire",
    "灰雁": "Grey Goose", "絕對": "Absolut", "皇冠": "Smirnoff", "思美洛": "Smirnoff",
    "北海巨妖": "Kraken", "摩根船長": "Captain Morgan", "百加得": "Bacardi",
    "唐胡立歐": "Don Julio", "豪帥": "Jose Cuervo", "克斯阿蘇爾": "Clase Azul",
    "酩悅": "Moët & Chandon", "凱歌": "Veuve Clicquot", "唐培里儂": "Dom Pérignon",
    "路易侯德爾": "Louis Roederer", "寶林傑": "Bollinger", "泰廷爵": "Taittinger",
    "奔富": "Penfolds", "開木斯": "Caymus", "康士嘉": "Kongsgaard", "樂華": "Domaine Lafage",
    "茅台": "Kweichow Moutai", "五糧液": "Wuliangye", "金門高粱": "Kinmen Kaoliang",
    "獺祭": "Dassai", "玉乃光": "Tamanohikari", "梅乃宿": "Umenoyado", "白鶴": "Hakutsuru",
    "鳳凰美田": "Hououbiden", "十四代": "Juyondai", "黑馬": "Kuroma",
}
_ZH_SORTED = sorted(ZH_EN, key=len, reverse=True)

# 英文寫法統一（全大寫、縮寫等）
EN_FIX = {
    "JOHNNIE WALKER": "Johnnie Walker", "MACALLAN": "The Macallan", "GLENLIVET": "The Glenlivet",
    "BALVENIE": "The Balvenie", "NIKKA": "Nikka", "SUNTORY": "Suntory",
}


def _english_part(text: str) -> str:
    """取出中英混寫裡的英文部分，例如 'Kongsgaard 康士嘉酒莊' → 'Kongsgaard'。"""
    parts = re.findall(r"[A-Za-z][A-Za-z0-9'’&.\- ]*[A-Za-z0-9.'’]", text or "")
    parts = [p.strip() for p in parts if len(p.strip()) >= 2]
    return parts[0] if parts else ""


def normalize(brand: str | None, name: str = "") -> str:
    """回傳英文品牌。brand 是網站給的品牌欄位（可能沒有），name 是品名。"""
    for src in (brand or "", name or ""):
        if not src:
            continue
        for zh in _ZH_SORTED:
            if zh in src:
                return ZH_EN[zh]
    if brand:
        en = _english_part(brand)
        if en:
            return EN_FIX.get(en.upper(), en)
        return brand.strip()
    en = _english_part(name)
    if en:
        # 品名的英文部分只取前兩個字當品牌
        return EN_FIX.get(en.upper(), " ".join(en.split()[:2]))
    return (name or "").split(" ")[0][:12]
