"""「這筆商品算不算一款辣醬」的規則（版本 `sauce-filter-3`）。

母體要的是辣醬，不是「名字裡有辣椒的所有食品」。第一版只看關鍵字，結果 USDA 那份
批次檔給了兩萬六千列，裡面有「Jalapeno Heat 洋芋片」「Peri Peri 調味豬里肌」
「加了紅辣椒的回鍋豆泥」。那些列數會讓 A8 的門檻好看，但它們不是辣醬——
**列數達標而內容是垃圾，事後從總表上完全看不出來**，所以規則要能擋住它。

第二版改成兩道閘，第三版把兩張表收緊（改的理由寫在各自的註解裡）。順序不能換：

1. **排除**先跑。「Hot Sauce T-Shirt」有 hot sauce 這三個字，但它是一件衣服；
   「Jalapeno Heat Potato Chips」有 jalapeno，但它是洋芋片。
2. **收錄**分兩條路：
   - 明講型：字串裡有 `hot sauce`、`sriracha`、`harissa`、`chili crisp` 這種
     本身就等於「這是一款辣醬」的詞 → 收。
   - 組合型：同時有**辣度詞**（habanero、ghost pepper、cayenne…）**和醬體詞**
     （sauce、oil、crisp、paste…）→ 收。只有其中一邊不算。

兩道閘都用「詞」為單位比對，不是字元；`ard` 不會命中 `aardvark`。
規則有版本號，而且每一筆都把命中的詞寫進 payload——半年後重跑時，
要分得出「市場上真的多了兩百款」與「我們把規則放寬了」。
"""
from __future__ import annotations

import re

VERSION = "sauce-filter-3"

#: 明講型：出現就等於「這是一款以辣椒為主體的醬」。不需要再看別的。
EXPLICIT = (
    "hot sauce", "hotsauce", "pepper sauce", "chili sauce", "chile sauce", "chilli sauce",
    "chili crisp", "chile crisp", "chilli crisp", "chili oil", "chile oil", "chilli oil",
    "chili paste", "chile paste", "chilli paste", "sriracha", "harissa", "sambal",
    "gochujang", "hot honey", "chamoy", "salsa picante", "salsa macha", "piri piri sauce",
    "peri peri sauce", "wing sauce", "buffalo sauce", "pepper mash", "pique",
    "aji sauce", "chilli garlic sauce", "chili garlic sauce", "yuzu kosho",
)

#: 辣度詞：說明它辣，但沒說它是醬。
#:
#: **`hot`、`spicy`、`pepper` 這三個字刻意不在這裡。** 第二版有它們，結果隨機抽樣抽到
#: 「Wawa Cranberry Sauce, For Junior Hot Hoagies」——`hot` ＋ `sauce` 就通過了，
#: 但那是蔓越莓醬。`hot sauce` 這個組合本來就在明講型清單裡，不需要靠這三個字補。
HEAT = (
    "habanero", "jalapeno", "jalapeño", "serrano", "ghost pepper", "bhut jolokia",
    "scorpion", "carolina reaper", "reaper", "scotch bonnet", "cayenne", "chipotle",
    "poblano", "ancho", "guajillo", "arbol", "datil", "calabrian", "aleppo",
    "fresno", "tabasco", "piri piri", "peri peri", "birds eye", "thai chili",
    "aji amarillo", "aji panca", "rocoto", "pequin", "trinidad", "naga", "scoville",
    "cascabel", "shishito", "hatch", "chile", "chili", "chilli", "chiles", "chilies",
    "capsaicin", "fatalii", "bhut", "jolokia",
)

#: 醬體詞：說明它是醬，但沒說它辣。
#:
#: `marinade`、`vinegar`、`juice` 拿掉了：醃料不是辣醬，而「辣椒＋醋」會把
#: 泡辣椒、辣味沙拉醬一起收進來。
SAUCY = ("sauce", "oil", "crisp", "paste", "condiment", "relish", "puree", "mash",
         "picante", "hot honey", "squeezins", "salsa")

#: 排除先跑。周邊商品、乾貨、器具、以及「本體是別的食物、只是加了辣椒」的那些。
EXCLUDE = (
    # 周邊與非食品
    "t-shirt", "tshirt", "t shirt", "hoodie", "sticker", "hat", "apparel", "sock",
    "mug", "glass", "poster", "koozie", "keychain", "magnet", "patch", "cookbook",
    "gift card", "giftcard", "e-gift", "subscription", "membership", "merch", "book",
    "advent calendar", "sampler pack", "gift set", "gift box", "heat pack", "bundle",
    "mystery box", "variety pack", "3 pack", "5 pack", "6 pack", "10 pack",
    # 乾貨、種子、粉末（不是醬）
    "seeds", "seed pack", "plant", "powder", "flakes", "dry rub", "spice rub",
    "seasoning", "salt", "peppercorn", "dried", "whole pepper",
    # 本體是別的食物
    "chips", "crisps", "pretzel", "popcorn", "peanut", "cracker", "jerky", "snack",
    "candy", "chocolate", "lollipop", "gummy", "cheese", "sausage", "hotdog", "hot dog",
    "bratwurst", "salami", "pepperoni", "bacon", "pork", "beef", "chicken breast",
    "tenderloin", "wings frozen", "burrito", "pizza", "pasta", "noodle", "ramen",
    "soup", "stew", "chili con carne", "beans", "rice", "tortilla", "bread", "bun",
    "ice cream", "yogurt", "hummus", "guacamole", "queso", "pimento cheese",
    "dressing", "mayo", "mayonnaise", "aioli", "ranch", "ketchup", "mustard",
    "bbq sauce", "barbecue sauce", "barbeque sauce", "teriyaki", "soy sauce",
    "worcestershire", "tartar sauce", "cocktail sauce", "pasta sauce", "pizza sauce",
    "alfredo", "marinara", "enchilada sauce", "taco sauce", "cheese sauce",
    "jam", "jelly", "fruit spread", "pickle", "olives", "tuna", "seafood", "shrimp",
    # 隨機抽樣抓到的假陽性（見 filter-3 的說明）
    "cranberry", "apple sauce", "applesauce", "curry sauce", "hoagie", "sandwich",
    "wrap", "bowl", "entree", "meal kit", "dumpling", "spring roll", "taco kit",
    "marinade", "glaze", "brine", "vinaigrette", "syrup", "smoothie", "juice",
    "tea", "coffee", "beer", "cider", "kombucha", "seltzer", "cocktail",
    # 「black pepper sauce」是黑胡椒醬，不是辣椒醬；但 "pepper sauce" 在明講型清單上，
    # 所以要在排除這一關就先攔下來。
    "black pepper",
)

_WORD = re.compile(r"[^a-z0-9]+")


def _blob(*parts: object) -> str:
    return " " + _WORD.sub(" ", " ".join(str(p or "") for p in parts).lower()).strip() + " "


def _hit(blob: str, needles: tuple[str, ...]) -> str:
    for n in needles:
        if " " + _WORD.sub(" ", n).strip() + " " in blob:
            return n
    return ""


def classify(title: str, product_type: str = "", tags: object = "",
             description: str = "") -> dict[str, object]:
    """回傳 {keep, reason, matched, filter_version}。理由一律寫出來，方便事後覆核。"""
    head = _blob(title, product_type, tags)
    excluded = _hit(head, EXCLUDE)
    if excluded:
        return {"keep": False, "reason": "excluded", "matched": excluded,
                "filter_version": VERSION}

    explicit = _hit(head, EXPLICIT)
    if explicit:
        return {"keep": True, "reason": "explicit", "matched": explicit,
                "filter_version": VERSION}

    heat, saucy = _hit(head, HEAT), _hit(head, SAUCY)
    if heat and saucy:
        return {"keep": True, "reason": "heat_plus_saucy", "matched": f"{heat}+{saucy}",
                "filter_version": VERSION}

    # 標題只寫產品名（"Reaper Squeezins"）時才看內文；內文一樣要過排除這一關。
    body = _blob(description)[:4000]
    if body.strip() and not _hit(body, EXCLUDE):
        explicit = _hit(body, EXPLICIT)
        if explicit:
            return {"keep": True, "reason": "explicit_in_description", "matched": explicit,
                    "filter_version": VERSION}
    return {"keep": False, "reason": "no_match", "matched": "", "filter_version": VERSION}


def keep(title: str, product_type: str = "", tags: object = "", description: str = "") -> bool:
    return bool(classify(title, product_type, tags, description)["keep"])
