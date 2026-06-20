-- supabase_schema.sql
-- Scout 行程＋確認狀態整合：Supabase（PostgreSQL）schema 的單一真實來源（SSOT）
--
-- 用途：
--   1. 全新環境 → 直接整份貼到 Supabase SQL Editor 執行，建好所有表。
--   2. 既有環境（珈欣已在 Supabase 介面手建 trips / itinerary_items）→ 同一份也能安全重跑，
--      因為所有 DDL 都是冪等（idempotent）：CREATE ... IF NOT EXISTS、ADD COLUMN IF NOT EXISTS、
--      DROP NOT NULL 重跑都不會出錯。
--
-- 設計重點（對應 spec）：
--   - 候選中狀態 = day_number IS NULL（不指定日期/時段），不需要額外欄位。
--   - 確認狀態用兩個布林值表達 spec 的兩軸：
--       confirm_required  → 必須確認(true) / 可以彈性(false)
--       is_confirmed      → 已確認(true)   / 未確認(false)
--   - day_number / start_time 改為可 NULL，候選項目才能無時段存在。
--   - 避開 PostgreSQL 保留字：使用者欄位用 username（不用 user）。
--   - start_time 用 text 存 'HH:MM'，與 Python 端 time_str_to_minutes() 的格式一致，
--     避免 Postgres time 型別回傳 'HH:MM:SS' 造成 split(":") 解析錯誤。

-- ──────────────────────────────────────────────
-- 1. trips（旅程）
-- ──────────────────────────────────────────────
create table if not exists trips (
    id          bigint generated always as identity primary key,
    username    text        not null,             -- 建立者；避開保留字 user
    name        text        not null,
    start_date  date        not null,
    end_date    date        not null,
    notes       text        default '',
    created_at  timestamptz default now()
);

-- ──────────────────────────────────────────────
-- 2. itinerary_items（行程項目，含候選與確認狀態）
-- ──────────────────────────────────────────────
create table if not exists itinerary_items (
    id               bigint generated always as identity primary key,
    trip_id          bigint  not null references trips(id) on delete cascade,
    day_number       integer,                      -- 可 NULL：NULL = 候選中（尚未排入某天）
    name             text    not null,
    category         text    default 'other',
    start_time       text,                         -- 可 NULL：'HH:MM'；候選中為 NULL
    duration_minutes integer default 60,
    location         text    default '',
    address          text    default '',
    booking_ref      text    default '',
    notes            text    default '',
    source           text    default 'manual',
    source_id        bigint,
    sort_order       integer default 0,
    confirm_required boolean not null default false, -- 必須確認 / 可以彈性
    is_confirmed     boolean not null default false, -- 已確認 / 未確認
    created_at       timestamptz default now()
);

-- ──────────────────────────────────────────────
-- 2b. wishlist（購物待買清單）
--     購物模組使用；Supabase 重構時被漏掉，這裡一併建回來，讓首頁「購物」可用。
-- ──────────────────────────────────────────────
create table if not exists wishlist (
    id              bigint generated always as identity primary key,
    username        text    not null,             -- 建立者；避開保留字 user
    name            text    not null,
    category        text    default '',
    estimated_price numeric default 0,
    status          text    default 'pending',    -- pending / purchased
    notes           text    default '',
    added_date      date    default current_date, -- 加入日期（沿用既有欄位，給預設值避免 NOT NULL 卡住）
    created_at      timestamptz default now()
);

-- 既有 wishlist 表（SQLite 時代留下）可能有 added_date NOT NULL 但無預設，
-- 補上預設值，讓沒帶 added_date 的 insert 也能成功。
alter table wishlist add column if not exists added_date date default current_date;
alter table wishlist alter column added_date set default current_date;

-- ──────────────────────────────────────────────
-- 3. trip_adjustments（調整歷史，沿用既有）
-- ──────────────────────────────────────────────
create table if not exists trip_adjustments (
    id            bigint generated always as identity primary key,
    trip_id       bigint not null references trips(id) on delete cascade,
    instruction   text,
    items_changed text,                            -- 存 JSON 字串（Supabase 不直接存 list）
    created_at    timestamptz default now()
);

-- ──────────────────────────────────────────────
-- 4. 既有環境的疊加遷移（在已手建好的表上補上本次異動）
--    這些語句重跑安全；全新環境上面已建好，這裡會是 no-op。
-- ──────────────────────────────────────────────

-- 4a. 讓 day_number / start_time 可為 NULL（支援候選中狀態）
alter table itinerary_items alter column day_number drop not null;
alter table itinerary_items alter column start_time drop not null;

-- 4b. 補上確認狀態兩軸欄位
alter table itinerary_items add column if not exists confirm_required boolean not null default false;
alter table itinerary_items add column if not exists is_confirmed     boolean not null default false;

-- ──────────────────────────────────────────────
-- 5. 索引（加速常用查詢：依旅程取項目、找候選、找未確認）
-- ──────────────────────────────────────────────
create index if not exists idx_items_trip       on itinerary_items (trip_id);
create index if not exists idx_items_trip_day    on itinerary_items (trip_id, day_number);
-- 候選項目（day_number IS NULL）的部分索引
create index if not exists idx_items_candidates  on itinerary_items (trip_id) where day_number is null;
-- 必須確認且未確認（優先儀表板的核心查詢）
create index if not exists idx_items_unconfirmed on itinerary_items (trip_id) where confirm_required and not is_confirmed;
create index if not exists idx_wishlist_user      on wishlist (username);

-- ──────────────────────────────────────────────
-- 6. Row Level Security（共享連結存取模型）
-- ──────────────────────────────────────────────
-- 身分機制：不做帳號系統，trip_id 即存取憑證（spec §5）。
-- 網頁版用 Supabase anon key 直接讀寫，因此需要允許 anon 角色存取這些表。
-- 【已知並刻意接受的風險】連結（trip_id）外流 = 任何人可讀寫該趟旅程全部資料。
--
-- 預設先「停用 RLS」最簡單可動（符合 spec 對簡單性的取捨）。若要稍微收斂，
-- 可改成啟用 RLS + 對 anon 開放 policy（下方註解版本）。二擇一，不要同時。

-- 版本 A（預設，最簡單）：停用 RLS ＋ 授權 anon/authenticated，publishable key 即可讀寫。
-- 注意：停用 RLS 還不夠，角色本身要有 table 權限（GRANT），否則會 42501 permission denied。
alter table trips            disable row level security;
alter table itinerary_items  disable row level security;
alter table trip_adjustments disable row level security;
alter table wishlist         disable row level security;

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete
    on trips, itinerary_items, trip_adjustments, wishlist
    to anon, authenticated;
-- identity 欄位的序列，授權後 anon 才能 insert
grant usage, select on all sequences in schema public to anon, authenticated;

-- 版本 B（可選，啟用 RLS 並對 anon 全開；效果與 A 相近但語意上更明確）：
-- alter table trips            enable row level security;
-- alter table itinerary_items  enable row level security;
-- alter table trip_adjustments enable row level security;
-- create policy anon_all_trips        on trips            for all to anon using (true) with check (true);
-- create policy anon_all_items        on itinerary_items  for all to anon using (true) with check (true);
-- create policy anon_all_adjustments  on trip_adjustments for all to anon using (true) with check (true);
