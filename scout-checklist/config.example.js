// config.example.js — 複製這個檔成 config.js，填入你的 Supabase 連線資訊。
//
// 這兩個值要去 Supabase 後台拿：
//   Project Settings → API
//   - SUPABASE_URL       = Project URL（例：https://abcd1234.supabase.co）
//   - SUPABASE_ANON_KEY  = Project API keys 裡的 "anon" / "public" key
//
// 注意：anon key 是「可公開」的金鑰，放在前端 JS 是 Supabase 的標準用法。
// 真正的存取控制來自分享連結裡的 trip_id（spec 的取捨：連結即憑證）。
// 不要把 service_role key 放進來——那把是後台用的，外洩會出事。

window.SCOUT_CONFIG = {
  SUPABASE_URL: "https://your-project.supabase.co",
  SUPABASE_ANON_KEY: "your-anon-key",
  GEMINI_API_KEY: "your-gemini-key",  // AI 匯入行程用（Google AI Studio），放前端已接受風險
};
