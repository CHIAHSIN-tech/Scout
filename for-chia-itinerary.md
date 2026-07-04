# 給 Chia — 行程表 spec 已完成 + 一個卡點請你處理

> 對應 spec：`specs/spec-scout-checklist-itinerary-view.md`
> 狀態：程式面全做完、demo 全綠。差你 un-pause Supabase 專案就全線跑通。

---

Chia，你那份行程表 spec（spec-scout-checklist-itinerary-view）我做完了，demo 全綠 🎉

三個 tab（確認清單 / 行程表 / 時間軸）、時間軸拖曳改時間 + 衝突警告 + 今天高亮、貼文字 AI 匯入、手機收合——AC-1~AC-9 都實作了。AI 匯入我用真的 Gemini 實測過：貼一段白話行程 → 自動拆成 8 筆、day/time/分類都對。

## ⚠️ 需要你做一件事（唯一卡點）

你的 Supabase 專案 `uarkccyqcqvgxukjcrey` **自動暫停了**（免費方案閒置約一週會 pause，現在 API 回 000）。請進 Supabase 後台把它 **Restore / Resume**。真實行程資料要它醒著才連得上；在那之前用 `?demo=1` 看得到長相，但存不進真資料。

## 回你 spec §10 的 5 個 open questions

1. **後端** → **Supabase**（就是你這個 fork 接的 `uarkccyqcqvgxukjcrey`），不是 Firebase。demo 提示文字已改掉，正式化沒問題。
2. **patchItem** → 已看過程式，它是通用 PATCH，**早就能直接改 day/time**（`scheduleItem` 就是用它寫 `day_number`+`start_time`）。**不是前置工作**，已在用。
3. **AI 解析 fallback** → 目前策略：AI 判斷不出 day/time 的項目，**預設放 Day 1、09:00**（不退回候選、不擋流程）。你列 Should，我先用最簡的；之後要改「待補時間」標記再說。
4. **API 金鑰外露** → 接受風險（跟 trip_id 同一套安全假設）。做法：**Gemini 金鑰只放本機 gitignored 的 `config.js`、不進 git**；只有可公開的 Supabase publishable key 寫死進程式。沒架 proxy。
5. **舊資料搬移** → 這版不做（你 Won't 已寫），要搬再手動。

## 兩個結構變動你要知道

- **app 搬家了**：scout-checklist 收進我們的 **private `Scout` repo**（跟 buylist 放一起），原本獨立的 `scout-checklist` repo 我已 **archive**。以後改這個 app 在 `Scout/scout-checklist/`，pull Scout 就有。
- **網址正式化（AC-9）**：選 **不公開部署**（不架 public GitHub Pages），就本機 / private 跑；`?demo=1` 預覽模式保留、沒 demo 參數就是接真資料的正式版。

你 Restore 專案後就全線跑通了。有問題敲我 🙌
