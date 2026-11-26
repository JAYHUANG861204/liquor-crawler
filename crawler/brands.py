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
    "野格": "Jägermeister", "絕對伏特加": "Absolut",
    "茅台": "Kweichow Moutai", "五糧液": "Wuliangye", "金門高粱": "Kinmen Kaoliang",
    "獺祭": "Dassai", "玉乃光": "Tamanohikari", "梅乃宿": "Umenoyado", "白鶴": "Hakutsuru",
    "鳳凰美田": "Hououbiden", "十四代": "Juyondai", "黑馬": "Kuroma",
    # 蘇格蘭威士忌酒廠 / 裝瓶商
    "布納哈本": "Bunnahabhain", "高原騎士": "Highland Park", "格蘭路思": "The Glenrothes", "吉拉": "Jura",
    "古董玩家": "Antiquary", "道格拉斯蘭恩": "Douglas Laing", "鄧肯泰勒": "Duncan Taylor", "格蘭艾樂奇": "GlenAllachie",
    "托本莫瑞": "Tobermory", "百齡譚": "Ballantine's", "拉佛格": "Laphroaig", "拉加維林": "Lagavulin",
    "羅夢德湖": "Loch Lomond", "塔木嶺": "Tamnavulin", "汀士頓": "Deanston", "坦度": "Tamdhu", "格蘭哥尼": "Glengoyne",
    "歐肯特軒": "Auchentoshan", "艾德多爾": "Edradour", "艾柏迪": "Aberfeldy", "克里尼利基": "Clynelish",
    "卡爾里拉": "Caol Ila", "帝王": "Dewar's", "失憶酒廠": "The Lost Distillery", "卡杜": "Cardhu",
    "格蘭帝": "Glen Scotia", "斯卡帕": "Scapa", "艾倫": "Arran", "齊侯門": "Kilchoman", "威海指南針": "Compass Box",
    "托明多": "Tomintoul", "卡梅倫橋": "Cameron Brig", "布萊德諾赫": "Bladnoch", "格蘭卡登": "Glencadam",
    "起瓦士": "Chivas Regal", "慕赫": "Mortlach", "阿貝": "Ardbeg", "格蘭花格": "Glenfarclas", "班瑞克": "BenRiach",
    "富特尼": "Old Pulteney", "達爾維尼": "Dalwhinnie", "歐本": "Oban", "龍摩恩": "Longmorn", "芬拉根": "Finlaggan",
    "波特阿希卡": "Port Askaig", "巴布萊爾": "Balblair", "格蘭陀崙特": "Glentauchers", "安努克": "anCnoc",
    "阿德莫爾": "Ardmore", "格蘭昆奇": "Glenkinchie", "皇家柏克萊": "Royal Brackla", "皇家藍勳": "Royal Lochnagar",
    "朗格羅": "Longrow", "仕高利達": "Scottish Leader", "老伯": "Old Parr", "格蘭莫雷": "Glen Moray",
    "格蘭多納": "Glendronach", "汀斯頓": "Deanston", "大摩": "The Dalmore", "雅柏": "Ardbeg",
    # 愛爾蘭 / 美國 / 加拿大 / 其他
    "布米爾": "Bushmills", "知更鳥": "Redbreast", "斯萊恩": "Slane", "都柏林自由": "Dublin Liberties",
    "吹哨者": "The Whistler", "肯塔基貓頭鷹": "Kentucky Owl", "布雷特": "Bulleit", "沃福": "Woodford Reserve",
    "四朵玫瑰": "Four Roses", "坦伯頓": "Templeton", "喬治迪凱爾": "George Dickel", "貝悅": "Basil Hayden",
    "伊凡威廉": "Evan Williams", "賽澤瑞克": "Sazerac", "水牛城": "Buffalo Trace", "西格拉姆": "Seagram's",
    "加拿大皇冠": "Crown Royal", "黑美人": "Black Velvet", "雅沐特": "Amrut", "保羅約翰": "Paul John",
    "麥格瑞": "Mackmyra", "史蘭利": "Slyrs", "星向": "Starward", "南投酒廠": "Nantou",
    # 日本
    "秩父": "Chichibu", "遊佐": "Yuza", "厚岸": "Akkeshi", "嘉之助": "Kanosuke", "富士山麓": "Kirin",
    "麒麟": "Kirin", "松井": "Matsui", "倉吉": "Kurayoshi", "長濱": "Nagahama", "戶河內": "Togouchi",
    "信州": "Mars", "津貫": "Mars", "駒之岳": "Mars", "櫻尾": "Sakurao", "輕井澤": "Karuizawa",
    # 其他烈酒 / 香檳 / 葡萄酒
    "巴黎之花": "Perrier-Jouët", "黑桃A": "Armand de Brignac", "庫克": "Krug", "雲霧之灣": "Cloudy Bay",
    "孟買藍寶石": "Bombay Sapphire", "猴子47": "Monkey 47", "水井坊": "Shui Jing Fang", "洋河": "Yang He",
    "塔牌": "Tapai", "馬爹利": "Martell",
}
_ZH_SORTED = sorted(ZH_EN, key=len, reverse=True)

# 英文寫法統一（全大寫、縮寫等）
EN_FIX = {
    "JOHNNIE WALKER": "Johnnie Walker", "MACALLAN": "The Macallan", "GLENLIVET": "The Glenlivet",
    "BALVENIE": "The Balvenie", "NIKKA": "Nikka", "SUNTORY": "Suntory",
}


# 由兩個字以上組成的英文品牌（從品名猜品牌時用）
EN_MULTI = [
    "Johnnie Walker", "Royal Salute", "Chivas Regal", "Monkey Shoulder", "Jack Daniel's", "Wild Turkey",
    "Four Roses", "Maker's Mark", "Jim Beam", "Grey Goose", "Captain Morgan", "Dead Rabbit", "Glen Grant",
    "Glen Moray", "Glen Scotia", "Old Pulteney", "Highland Park", "Louis Roederer", "Veuve Clicquot",
    "Dom Perignon", "Moët & Chandon", "Perrier Jouet", "Don Julio", "Clase Azul", "Five Farms", "Grand Marnier",
    "Bombay Sapphire", "Mount Gay", "Rémy Martin", "Remy Martin", "Cloudy Bay", "Black Velvet", "Crown Royal",
    "Buffalo Trace", "Woodford Reserve", "Compass Box", "Douglas Laing", "Duncan Taylor", "Loch Lomond",
    "Port Askaig", "Paul John", "Kentucky Owl", "Old Parr", "Scottish Leader", "Gut Hermannsberg",
    "Pierre Antonin", "Alex Gambal", "Domaine Lafage", "Louis Morette", "Oak Farm", "Kweichow Moutai",
    "Armand de Brignac", "Monkey 47", "Dead Rabbit", "The Whistler", "Evan Williams", "Basil Hayden",
]
_EN_MULTI_L = sorted(EN_MULTI, key=len, reverse=True)
CJK = re.compile(r"[\u3400-\u9fff]")
_DESCRIPTOR = re.compile(r"莊園|系列|限定|限量|珍藏|典藏|原酒|單桶|雙桶|酒莊|蒸餾所|酒廠|紅牌|白牌|黑牌|調和|單一|純麥|麥芽|年|週年|版")


def _english_brand(text: str) -> str:
    """從英文品名取品牌：先比對多字品牌，否則取第一個字（The 開頭取兩個字）。"""
    en = _english_part(text)
    if not en:
        return ""
    low = en.lower()
    for b in _EN_MULTI_L:
        if low.startswith(b.lower()):
            return b
    words = re.sub(r"\d+$", "", en).split()
    if not words:
        return ""
    if words[0].lower() == "the" and len(words) > 1:
        return " ".join(words[:2])
    return words[0]


def _chinese_head(name: str) -> str:
    """全中文品名：取酒類名稱、數字、英文之前的那段，再去掉「系列、限定」這類描述字，最多 6 個字。"""
    head = re.split(r"[A-Za-z\d\s（(／/\-]|琴酒|威士忌|白蘭地|干邑|葡萄酒|紅酒|白酒|粉紅酒|香檳|氣泡酒|清酒|伏特加|"
                    r"蘭姆酒|龍舌蘭|利口酒|啤酒|梅酒|高粱|甜酒|雪莉酒|波特酒|"
                    r"白稍南|白蘇維濃|長相思|夏多內|霞多麗|卡本內|梅洛|黑皮諾|希哈|麗絲玲|格那希|田帕尼優|山吉歐維榭|"
                    r"內比歐露|馬爾貝克|金粉黛|灰皮諾|副牌|正牌|阿蒙提雅多|菲諾|歐洛羅索|佩德羅", name or "")[0]
    head = re.sub(r"^(南非|法國|西班牙|義大利|意大利|智利|澳洲|美國|紐西蘭|德國|日本|蘇格蘭|愛爾蘭|阿根廷|葡萄牙|台灣)", "", head)
    m = _DESCRIPTOR.search(head)
    if m and m.start() >= 2:
        head = head[:m.start()]
    return head[:6]


def _english_part(text: str) -> str:
    """取出中英混寫裡的英文部分，例如 'Kongsgaard 康士嘉酒莊' → 'Kongsgaard'。"""
    parts = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’&.\- ]*[A-Za-zÀ-ÖØ-öø-ÿ0-9.'’]", text or "")
    unit = re.compile(r"^(\d+\s*)?(ml|cl|l|lt|ltr|abv|vol|yo|yrs?|years?|x)$", re.I)
    parts = [p.strip() for p in parts if len(p.strip()) >= 2 and not unit.match(p.strip())]
    return parts[0] if parts else ""


EXTRA_CANON = ["Louis XIII", "Dewar's", "Rémy Martin", "Moët & Chandon", "Perrier-Jouët", "Dom Pérignon",
               "Hennessy", "Martell", "Courvoisier", "Penfolds", "Kavalan", "Yamazaki", "Hibiki", "Hakushu"]


def _ckey(b: str) -> str:
    import unicodedata
    b = unicodedata.normalize("NFKD", b).encode("ascii", "ignore").decode()
    b = re.sub(r"^the\s+", "", b.strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", b.lower())


# 同一個品牌的不同寫法統一成一種（The Glen Grant / GLEN GRANT → Glen Grant；DEWARS → Dewar's）
CANON = {}
for _b in list(ZH_EN.values()) + EN_MULTI + EXTRA_CANON:
    CANON.setdefault(_ckey(_b), _b)


def _canon(b: str) -> str:
    return CANON.get(_ckey(b), b) if b else b


def _fix_case(b: str) -> str:
    """全大寫的品牌改成首字大寫（WARWICK → Warwick），4 個字以內的縮寫保留（JD&S、CASS）。"""
    if b.isupper() and len(re.sub(r"[^A-Z]", "", b)) > 4:
        return " ".join(w.capitalize() if w.isalpha() else w for w in b.split())
    return b


def _normalize(brand: str | None, name: str = "") -> str:
    """回傳英文品牌。brand 是網站給的品牌欄位（可能沒有），name 是品名。

    順序：中文對照表 → 網站品牌欄位的英文 → 品名的英文（品名開頭是英文時）→ 品名開頭的中文。
    """
    for src in (brand or "", name or ""):
        for zh in _ZH_SORTED:
            if zh in src:
                return ZH_EN[zh]
    if brand:
        en = _english_part(brand)
        if en:
            return _fix_case(EN_FIX.get(en.upper(), en))
        return brand.strip()
    name = (name or "").strip()
    if name and not CJK.match(name[0]):
        en = _english_brand(name)
        if en:
            return _fix_case(EN_FIX.get(en.upper(), en))
    head = _chinese_head(name)
    if head:
        return head
    return _fix_case(_english_brand(name)) or name[:10]


def normalize(brand: str | None, name: str = "") -> str:
    return _canon(_normalize(brand, name))
