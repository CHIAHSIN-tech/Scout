# 成分結構化的覆蓋率（A20）

**這份報告沒有通過門檻。** 它的用途是把兩件看不見的事變成數字。

## 1. 有 1211 / 1211 列（**100.0%**）從來沒有被交叉驗證過

`composition_disagreement` 只有在**照片與 FDC 都有成分表**時才算得出來。
只有單一來源的列不是「一致」，是**沒比過**——而它在表上跟比過的一模一樣。

- 兩邊都有、比得起來的：0 列
- 其中有欄位不一致的：0 列

## 2. 三層來源各佔多少

| 來源 | 當主要來源的列數 | 有提供資料的列數 |
|---|---|---|
| label_photo | 0 | 0 |
| fdc | 1200 | 1200 |
| storefront_text | 11 | 11 |

`label_photo` 是實物標籤的逐字轉錄，**最準**；`storefront_text` 最弱。

## 3. 各欄位的填充率

| 欄位 | 有值的列數 | 比例 |
|---|---|---|
| first_ingredient | 1211 | 100.0% |
| ingredient_count | 1211 | 100.0% |
| sodium_per_100g | 1139 | 94.1% |
| pepper_form | 1074 | 88.7% |
| acidifier | 1074 | 88.7% |
| calories_per_100g | 1065 | 87.9% |
| peppers | 994 | 82.1% |
| pepper_ordinal | 994 | 82.1% |
| sugar_per_100g | 900 | 74.3% |
| sweetener | 698 | 57.6% |
| thickener | 562 | 46.4% |
| preservative | 376 | 31.0% |
| oil_type | 346 | 28.6% |
| water_first | 221 | 18.2% |
| allergens | 188 | 15.5% |
| umami_adds | 134 | 11.1% |
| fermented | 113 | 9.3% |
| colorant | 109 | 9.0% |
| organic_certified | 94 | 7.8% |
| has_capsaicin_extract | 43 | 3.6% |
| gluten_free_claim | 4 | 0.3% |
| manufacturer_name | 0 | 0.0% |
| vegan_claim | 0 | 0.0% |
