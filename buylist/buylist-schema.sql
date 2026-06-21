-- buylist-schema.sql
-- BuyList tracer bullet 用的 Supabase 表 + 即時同步設定。
-- 與 Scout 共用同一個 Supabase 專案（單一後端）。
-- 在 Supabase SQL Editor 整份貼上、按 Run。冪等，可重跑。

-- 1. 表（這版 tracer bullet 只需要 name；之後 loop 再加價格/迫切度等欄位）
create table if not exists buylist_items (
    id         bigint generated always as identity primary key,
    name       text not null,
    created_at timestamptz default now()
);

-- 2. 權限（無登入；anon/publishable key 直接讀寫——已同意權限全開）
alter table buylist_items enable row level security;
drop policy if exists buylist_anon_all on buylist_items;
create policy buylist_anon_all on buylist_items for all to anon using (true) with check (true);
grant usage on schema public to anon;
grant select, insert, update, delete on buylist_items to anon;
grant usage, select on all sequences in schema public to anon;

-- 3. 即時同步：把表加進 Supabase Realtime 的發佈清單
--    （replica identity full 讓 update/delete 也帶完整舊值）
alter table buylist_items replica identity full;
do $$
begin
  alter publication supabase_realtime add table buylist_items;
exception when duplicate_object then null;  -- 已加過就略過
end $$;
