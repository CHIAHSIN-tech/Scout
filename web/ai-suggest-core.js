// ai-suggest-core.js — AI 生成行程的純邏輯（問題清單、prompt 組裝、回應正規化）。
//
// 為什麼獨立成一支：同一套邏輯要被三個地方用——
//   1. 瀏覽器（checklist.js 的問答 UI 與寫入）
//   2. Netlify Function（ai-suggest.js 組 prompt）
//   3. scripts/check-ai-suggest.mjs（驗收，用 node:vm 餵假的 window 求值）
// 規格明訂「共用邏輯不得存在第二份實作」，所以這裡是唯一來源。
//
// 無 build step（ADR-010）：不用 ESM、不打包，掛全域物件讓三邊都讀得到。
//
// 參照來源是已退役的 Streamlit `page_ai_suggest.py`。行為 parity，但**不移植它的四個缺陷**
// （category 無白名單、day 未夾範圍、確認兩軸未設、勾選狀態雙軌）——見 specs/inventory-ai-suggest.md。

(function (root) {
  "use strict";

  // ── 六題，依序問（原文照搬參照系統）──
  var QUESTIONS = [
    { key: "destination", label: "你們打算去哪裡旅行？", type: "text", placeholder: "例：沖繩、京都、首爾" },
    { key: "days",        label: "預計幾天幾夜？",       type: "text", placeholder: "例：3 天 2 夜" },
    { key: "people",      label: "幾個人一起去？有哪些成員？", type: "text", placeholder: "例：2 大人 1 小孩、情侶、家庭" },
    { key: "preference",  label: "旅遊偏好是什麼？",     type: "multiselect",
      options: ["🍜 在地美食", "🏛️ 歷史景點", "🌿 自然風景", "🛍️ 購物",
                "♨️ 溫泉 / 泡湯", "🎌 文化體驗", "🎡 主題樂園",
                "🍺 酒吧 / 夜生活", "☕ 咖啡廳巡禮", "🏖️ 海灘 / 戶外活動"] },
    { key: "budget",      label: "每人每天大約的預算是多少？", type: "text", placeholder: "例：3000 台幣、不限制" },
    { key: "extra",       label: "還有什麼特別需求或想避開的？（可跳過）", type: "text",
      placeholder: "例：不喜歡太多步行、需要親子友善、素食", optional: true },
  ];

  var VALID_CATEGORIES = ["restaurant", "hotel", "attraction", "shopping", "transport", "other"];
  var DEFAULT_TIME = "09:00";
  var DEFAULT_DURATION = 60;

  // ── Prompt（五條規則照搬參照系統）──
  function buildPrompt(answers) {
    answers = answers || {};
    var v = function (k) { var s = String(answers[k] == null ? "" : answers[k]).trim(); return s || "未提供"; };
    var extra = String(answers.extra == null ? "" : answers.extra).trim() || "無";
    return "你是一位專業的旅遊規劃師。請根據以下資訊，為使用者規劃一份詳細的旅遊行程建議。\n\n" +
      "旅遊資訊：\n" +
      "- 目的地：" + v("destination") + "\n" +
      "- 天數：" + v("days") + "\n" +
      "- 成員：" + v("people") + "\n" +
      "- 偏好：" + v("preference") + "\n" +
      "- 預算：" + v("budget") + "\n" +
      "- 特殊需求：" + extra + "\n\n" +
      "請回傳一個 JSON 陣列，每個元素代表一個行程項目，格式如下：\n" +
      "[\n  {\n" +
      '    "day": 1,\n' +
      '    "name": "景點或餐廳名稱",\n' +
      '    "category": "attraction 或 restaurant 或 shopping 或 hotel 或 transport 或 other",\n' +
      '    "start_time": "HH:MM",\n' +
      '    "duration_minutes": 90,\n' +
      '    "location": "所在區域或地址",\n' +
      '    "notes": "簡短說明或推薦原因"\n' +
      "  }\n]\n\n" +
      "規則：\n" +
      "1. 根據天數安排每天的行程，早上約 09:00 開始，合理分配時間\n" +
      "2. 景點大約 90-120 分鐘，餐廳 60-90 分鐘，購物 60-90 分鐘\n" +
      "3. 每天安排 4-6 個項目，包含早餐、午餐、晚餐和景點\n" +
      "4. 行程之間預留合理的移動時間\n" +
      "5. 只回傳 JSON 陣列，不要任何說明文字或 markdown";
  }

  // ── 解析 AI 回傳 ──
  // 錯誤訊息一律說明「下一步做什麼」，不丟裸錯誤給使用者。
  function parseSuggestions(raw) {
    var text = String(raw == null ? "" : raw).trim();
    if (!text) {
      return { error: "AI 沒有回傳任何內容。請按「重新生成」再試一次；若持續發生，換個說法描述目的地。" };
    }
    // 去掉 ``` / ```json 圍欄（同參照系統）
    var cleaned = text.replace(/```json/gi, "").replace(/```/g, "").trim();
    var parsed = null;
    try {
      parsed = JSON.parse(cleaned);
    } catch (e) {
      // 退一步：從第一個 [ 到最後一個 ] 再試（AI 偶爾會多寫一句話）
      var s = cleaned.indexOf("["), t = cleaned.lastIndexOf("]");
      if (s !== -1 && t !== -1 && t > s) {
        try { parsed = JSON.parse(cleaned.slice(s, t + 1)); } catch (e2) { parsed = null; }
      }
      if (parsed === null) {
        return { error: "AI 回傳的格式無法解析成行程清單。請按「重新生成」再試一次。" };
      }
    }
    if (!Array.isArray(parsed)) {
      return { error: "AI 回傳的格式不正確（不是行程陣列）。請按「重新生成」再試一次。" };
    }
    if (parsed.length === 0) {
      return { error: "AI 沒有給出任何行程項目。試著把目的地或天數寫具體一點再生成一次。" };
    }
    return { items: parsed };
  }

  // ── 正規化成可寫入 itinerary_items 的欄位 ──
  // 這裡就是不移植參照系統缺陷的地方：category 走白名單、day 夾到旅程範圍、
  // 確認兩軸明確寫 false（不能留 null）。
  function normaliseItem(row, totalDays) {
    row = row || {};
    var name = String(row.name == null ? "" : row.name).trim();
    if (!name) return null;                       // 沒有名稱的項目直接丟掉，不寫「未命名」進資料庫

    var day = parseInt(row.day, 10);
    if (!isFinite(day) || day < 1) day = 1;
    if (totalDays > 0 && day > totalDays) day = totalDays;   // 缺陷 2：夾到旅程實際天數

    var time = String(row.start_time == null ? "" : row.start_time).trim();
    if (!/^([01]?\d|2[0-3]):[0-5]\d$/.test(time)) time = DEFAULT_TIME;
    else { var p = time.split(":"); time = ("0" + p[0]).slice(-2) + ":" + p[1]; }

    var dur = parseInt(row.duration_minutes, 10);
    if (!isFinite(dur) || dur <= 0) dur = DEFAULT_DURATION;

    var cat = String(row.category == null ? "" : row.category).trim().toLowerCase();
    if (VALID_CATEGORIES.indexOf(cat) === -1) cat = "other";   // 缺陷 1：白名單

    return {
      name: name,
      day_number: day,
      start_time: time,
      duration_minutes: dur,
      category: cat,
      location: String(row.location == null ? "" : row.location).trim(),
      notes: String(row.notes == null ? "" : row.notes).trim(),
      confirm_required: false,   // 缺陷 3：兩軸要明確寫，不能留 null
      is_confirmed: false,
      source: "ai",
    };
  }

  function normaliseAll(rows, totalDays) {
    var out = [];
    for (var i = 0; i < (rows || []).length; i++) {
      var n = normaliseItem(rows[i], totalDays);
      if (n) out.push(n);
    }
    return out;
  }

  // 依天分組，天數由小到大（結果畫面用）
  function groupByDay(items) {
    var map = {};
    (items || []).forEach(function (it) {
      var d = it.day_number || 1;
      (map[d] = map[d] || []).push(it);
    });
    return Object.keys(map).map(Number).sort(function (a, b) { return a - b; })
      .map(function (d) {
        return { day: d, items: map[d].slice().sort(function (a, b) {
          return String(a.start_time).localeCompare(String(b.start_time)); }) };
      });
  }

  root.ScoutAiSuggest = {
    QUESTIONS: QUESTIONS,
    VALID_CATEGORIES: VALID_CATEGORIES,
    DEFAULT_TIME: DEFAULT_TIME,
    DEFAULT_DURATION: DEFAULT_DURATION,
    buildPrompt: buildPrompt,
    parseSuggestions: parseSuggestions,
    normaliseItem: normaliseItem,
    normaliseAll: normaliseAll,
    groupByDay: groupByDay,
  };
})(typeof window !== "undefined" ? window : this);
