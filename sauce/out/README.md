# 輸出目錄

**看 `<執行日期>/` 那幾個資料夾，不要看這一層的 CSV。**

從 v3（A48）起，`sauce.export` 每次執行寫進自己的目錄：

```
sauce/out/2026-09-20/sauce_catalog-v1.csv
sauce/out/2026-09-20/sauce_buyable-v1.csv
sauce/out/2026-09-20/sauce_reviews-v1.csv
```

不覆蓋上一次是刻意的：半年後要回答「這款醬是這次才出現的，還是上次漏抓」，
唯一的辦法是兩次的輸出都還在。`sauce.trend` 就是拿這些目錄互相比對。

## 這一層的三個 CSV 是舊的

`sauce_catalog-v1.csv`、`sauce_buyable-v1.csv`、`sauce_reviews-v1.csv`
是 v3 之前的輸出位置，內容停在 2026-09-19（7,037 列）。
**它們跟現在的資料不一樣，但檔名看不出來**——這正是要改成每次一個目錄的原因。

要不要把它們刪掉是 Stanley 決定的事（它們在版控裡，刪掉會動到歷史上的檔案）。
在決定之前，這份說明就是那面警告牌。
