// config.example.js — 複製這個檔成 config.js，填入你的連線資訊。
//
// Supabase（必填，讀寫行程資料）：去 Supabase 後台拿
//   Project Settings → API
//   - SUPABASE_URL       = Project URL（例：https://abcd1234.supabase.co）
//   - SUPABASE_ANON_KEY  = Project API keys 裡的 "anon" / "public" key
//
// Gemini（選填，只有「AI 匯入行程」會用到）：去 Google AI Studio 拿 API key
//   - GEMINI_API_KEY     = 你的 Gemini API 金鑰
//   - GEMINI_MODEL       = 模型名稱（可省略，預設 gemini-3-flash-preview）
//
// 注意：anon key 是「可公開」的金鑰，放在前端 JS 是 Supabase 的標準用法。
// 真正的存取控制來自分享連結裡的 trip_id（spec 的取捨：連結即憑證）。
// 不要把 service_role key 放進來——那把是後台用的，外洩會出事。
//
// ⚠️ Gemini 金鑰風險（spec Open Question 4）：本站是純前端靜態網頁，GEMINI_API_KEY
//    會出現在瀏覽器可見的程式碼中。這沿用與 trip_id / anon key 相同的安全假設
//    （可公開、靠連結保護）。若不可接受，請改在後端 / serverless function 代呼叫，
//    並把金鑰留在伺服器端；不確定就先別填，AI 匯入會顯示提示而非壞掉。

window.SCOUT_CONFIG = {
  SUPABASE_URL: "https://your-project.supabase.co",
  SUPABASE_ANON_KEY: "your-anon-key",

  // 選填：AI 匯入行程才需要
  GEMINI_API_KEY: "your-gemini-key",
  GEMINI_MODEL: "gemini-3-flash-preview",
};
