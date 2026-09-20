"""事件契約（N1 凍結，其餘節點不得改）。

這一份是唯一的真相來源：命名空間、來源清單、event_type 清單、entity_id 模板。
抓取層、抽取層、比對層、檢查器全部從這裡讀，沒有第二份定義。

## 兩個與 spec 字面不同的地方（見 DECISIONS.md D1、D2）

1. 連結事件叫 `entity.linked`，不是 `sauce.entity.linked`。
   evdb 核心的 `evdb orphans` 是硬寫 `event_type = 'entity.linked'` 找連結的
   （`evdb/query.py`），改名字會讓每一筆觀察都變成孤兒，A27 直接破功。
   領域前綴留在被連結的觀察事件上（`sauce.*`），連結本身走核心慣例，與 `domains/ma` 一致。

2. 評論與觀察的 entity_id 都走核心的 `src:` 命名空間。
   同樣是 `evdb orphans` 的硬條件（`entity_id LIKE 'src:%'`）。一筆觀察在被比對器連上之前，
   本來就還沒解析成真實實體，`src:` 正是核心給這種狀態的命名空間。
   `sauce:` / `brand:` / `review:` 是比對之後才出現的身分。
"""
from __future__ import annotations

CONTRACT_VERSION = "sauce-contract-1"

#: 連結事件的 event_type。核心的 orphans 查詢認這個字串（見模組說明）。
LINK_EVENT = "entity.linked"

#: 領域前綴：`evdb orphans --domain sauce` 用它篩 event_type
DOMAIN = "sauce"

# ---- 命名空間 ----------------------------------------------------------------
NAMESPACES: dict[str, str] = {
    "sauce": "一款辣醬產品（不分瓶容量）：sauce:<brand_key>|<product_key>",
    "brand": "一個辣醬品牌或製造商：brand:<brand_key>",
    "gtin": "GTIN-14（UPC 前面補零到 14 位）：gtin:<14 位數字>",
    "review": "一篇專業評論：review:<outlet_key>:<url_sha1_12>",
    "maker": "一個製造者（代工廠）：maker:<maker_key>",
    "label": "一張標籤照片：label:<image_sha256_12>",
    "outlet": "一個評論發布單位：outlet:<outlet_key>",
}

# ---- 來源 --------------------------------------------------------------------
#: 產品層：決定母體有哪些辣醬
PRODUCT_SOURCES: dict[str, str] = {
    "fdc": "USDA FoodData Central Branded Foods 批次檔（帶 GTIN 的品牌食品母體）",
    "off": "Open Food Facts 美國產品匯出（補 FDC 漏掉的進口與小廠）",
    "shopify": "獨立品牌與專賣零售的 Shopify 公開 /products.json",
    "woo": "WooCommerce Store API 公開商品端點",
    "webshop": "既不是 Shopify 也不是 Woo 的店：只讀站方自己宣告的 schema.org／OpenGraph",
    "wikidata": "Wikidata SPARQL：辣醬類別的品項與品牌",
    "wikipedia": "Wikipedia 條目（List of hot sauces 等）",
    "awards": "Scovie Awards / World Hot Sauce Awards / NYC Hot Sauce Expo 得獎名單",
    "hotones": "每季選醬名單（來自 Heatonist 的 season pack 商品頁與編輯型報導，不經影音平台）",
    "reddit": "Reddit 官方 Data API —— 只用來發現名字，永遠不產生評論事件（A20）",
}

#: 標籤影像層（v3）。實物標籤是成分與營養的第一來源。
IMAGE_SOURCES: dict[str, str] = {
    "off_image": "Open Food Facts 貢獻者拍的成分／營養面板（CC BY-SA 3.0，不重新散布）",
    "storefront_image": "Shopify 商品圖（多為正面瓶身，背標覆蓋率低，當補充）",
}

#: 評論層：決定判斷。這三個是唯一可以產生 sauce.review.* 的來源。
REVIEW_SOURCES: dict[str, str] = {
    "outlet_web": "白名單內 outlet 的評論文章",
    "podcast_transcript": "Podcast RSS 裡發布者自己公開的逐字稿",
    "print_archive": "有公開線上版的雜誌／報紙評論",
}

#: 使用者生成內容：只准產生 sauce.observation.mention（A20 的擋牆）
UGC_SOURCES: frozenset[str] = frozenset({"reddit", "retailer_widget", "marketplace", "forum_ugc"})

SOURCES: dict[str, str] = {**PRODUCT_SOURCES, **IMAGE_SOURCES, **REVIEW_SOURCES}

#: 來源階層。視圖的 `tiers` 欄用它回答「這一列是誰看到的」——
#: 只被第 4 層看到的產品，和被第 1 層看到的產品，證據強度差很多，
#: 但如果不把階層寫成欄位，兩者在總表上長得一模一樣。
SOURCE_TIER: dict[str, str] = {
    "fdc": "1_population", "off": "1_population",
    "shopify": "2_longtail", "woo": "2_longtail", "webshop": "2_longtail",
    "wikidata": "3_roster", "wikipedia": "3_roster", "awards": "3_roster",
    "hotones": "3_roster",
    "reddit": "4_mention",
    "outlet_web": "5_review", "podcast_transcript": "5_review", "print_archive": "5_review",
    "off_image": "6_label", "storefront_image": "6_label",
}

#: 可購性的強弱順序。同一款醬在不同來源有不同說法時，取最強的那個，並記下它的出處。
AVAILABILITY_RANK: dict[str, int] = {
    "retail_listing": 4, "brand_us_site": 3, "discontinued": 2,
    "mention_only": 1, "unknown": 0,
}

# ---- event_type --------------------------------------------------------------
EV_PRODUCT = "sauce.observation.product"
EV_MENTION = "sauce.observation.mention"
EV_AVAILABILITY = "sauce.observation.availability"
EV_LINEUP = "sauce.observation.lineup"
EV_REVIEW = "sauce.review.published"
EV_VERDICT = "sauce.review.verdict"
EV_PARSED = "sauce.extraction.parsed"
EV_LABEL_IMAGE = "sauce.label.image"
EV_LABEL_READ = "sauce.label.read"
EV_COMPOSITION = "sauce.composition.derived"
EV_HEAT_CLAIM = "sauce.heat.claim"
EV_HEAT_ORDER = "sauce.heat.ordering"

EVENT_TYPES: dict[str, str] = {
    EV_PRODUCT: "一筆目錄型來源記錄（fdc / off / shopify / woo / webshop）",
    EV_MENTION: "一次提及，只有名字（wikidata / wikipedia / awards / hotones / reddit）",
    EV_AVAILABILITY: "一次在美國零售或品牌官網看到上架",
    EV_LINEUP: "某季某集的選醬名單（含第幾棒與標榜 SHU）",
    EV_REVIEW: "一篇專業評論（payload 只放 metadata，正文在 raw store）",
    EV_VERDICT: "該評論對某一款醬的評語（一篇多款就多筆）",
    EV_PARSED: "模型對某筆觀察的解析結果（帶 model_id 與 prompt_version）",
    EV_LABEL_IMAGE: "一張標籤照片（payload 只放 metadata，圖片在 raw store）",
    EV_LABEL_READ: "模型對某張照片的逐字轉錄（帶 model_id 與 prompt_version）",
    EV_COMPOSITION: "規則從文字算出的結構化成分／營養（帶 rules_version，無 model）",
    EV_HEAT_CLAIM: "一筆辣度宣稱（帶 source）",
    EV_HEAT_ORDER: "一筆排序事實（棒次／零售商分級／品牌線內順序）",
}

#: 只有這些 event_type 可以帶 review 語意，A20 靠它判斷越界
REVIEW_EVENT_TYPES: frozenset[str] = frozenset({EV_REVIEW, EV_VERDICT})

# ---- 值域（A10 第二層、A16、A21 用同一份定義）--------------------------------
US_AVAILABILITY = ("retail_listing", "brand_us_site", "mention_only", "discontinued", "unknown")
STANCE = ("positive", "mixed", "negative", "descriptive")
MODALITY = ("text", "spoken_transcript")
ARTICLE_KIND = ("single", "roundup", "ranking", "guide")
DISCLOSURE = ("samples_provided", "purchased", "undisclosed", "affiliate")
ADMISSION_BASIS = ("masthead", "named_author_series", "methodology_page")
OUTLET_TIER = ("1_methodology", "2_editorial", "3_listicle")
CONFLICT_OF_INTEREST = ("none", "affiliate", "sells_products")

#: 規則版本。折疊規則或比對規則改了就換版本，舊的 view 目錄不覆寫。
NAMES_VERSION = "sauce-names-1"
MATCHER_VERSION = "sauce-match-1"
REVIEW_LINK_VERSION = "sauce-reviewlink-1"


# ---- entity_id 模板 ----------------------------------------------------------
def sauce_id(brand_key: str, product_key: str) -> str:
    return f"sauce:{brand_key}|{product_key}"


def brand_id(brand_key: str) -> str:
    return f"brand:{brand_key}"


def gtin_id(gtin14: str) -> str:
    return f"gtin:{gtin14}"


def review_id(outlet_key: str, url_sha1_12: str) -> str:
    return f"review:{outlet_key}:{url_sha1_12}"


def outlet_id(outlet_key: str) -> str:
    return f"outlet:{outlet_key}"


def maker_id(maker_key: str) -> str:
    return f"maker:{maker_key}"


def label_id(image_sha256: str) -> str:
    return f"label:{image_sha256[:12]}"


def observation_id(source: str, key: str) -> str:
    """尚未解析成真實實體的觀察。核心的 orphans 只看得到 `src:` 開頭的（見模組說明）。"""
    return f"src:{source}:{key}"


def as_dict() -> dict[str, object]:
    """給 state/graph-state-sauce.json 的 `contract` 欄位用的可序列化版本。"""
    return {
        "contract_version": CONTRACT_VERSION,
        "domain": DOMAIN,
        "link_event": LINK_EVENT,
        "namespaces": NAMESPACES,
        "sources": SOURCES,
        "ugc_sources": sorted(UGC_SOURCES),
        "event_types": EVENT_TYPES,
        "entity_id_templates": {
            "sauce": "sauce:<brand_key>|<product_key>",
            "brand": "brand:<brand_key>",
            "gtin": "gtin:<14 位數字>",
            "review": "review:<outlet_key>:<url_sha1_12>",
            "outlet": "outlet:<outlet_key>",
            "observation": "src:<source>:<key>",
        },
        "versions": {"names": NAMES_VERSION, "matcher": MATCHER_VERSION,
                     "review_link": REVIEW_LINK_VERSION},
    }
