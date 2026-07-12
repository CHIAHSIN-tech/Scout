-- buylist-schema.sql — BuyList 完整 schema（冪等，可重跑）。
-- 在「你自己的」Supabase 專案（kdmmjlaajqxjmiahfvos）SQL Editor 整份貼上、按 Run。

-- 1. 物品表（tracer bullet 只有 name；這裡補齊全部欄位）
create table if not exists buylist_items (
    id            bigint generated always as identity primary key,
    name          text not null,
    price         numeric  default 0,
    urgency       text     default 'maybe',     -- need 需要 / want 想要 / maybe 再看看
    accessibility text     default 'tw_easy',   -- tw_easy 台灣易 / overseas 需國外 / rare 稀有難找
    this_month    boolean  default true,        -- 本月想買 / 之後再說
    bought        boolean  default false,
    added_by      text     default '',          -- 誰加的
    note          text     default '',
    link          text     default '',
    category      text     default '其他',       -- 物品分類
    recurring_cost numeric default 0,            -- 後續成本（耗材/訂閱，每月）
    created_at    timestamptz default now()     -- 冷卻期「想買 N 天」用
);
alter table buylist_items add column if not exists price         numeric default 0;
alter table buylist_items add column if not exists urgency       text default 'maybe';
alter table buylist_items add column if not exists accessibility text default 'tw_easy';
alter table buylist_items add column if not exists this_month    boolean default true;
alter table buylist_items add column if not exists bought        boolean default false;
alter table buylist_items add column if not exists added_by      text default '';
alter table buylist_items add column if not exists note          text default '';
alter table buylist_items add column if not exists link          text default '';
alter table buylist_items add column if not exists category       text default '其他';
alter table buylist_items add column if not exists recurring_cost numeric default 0;
alter table buylist_items add column if not exists starred        boolean default false;   -- 已買星號收藏（可回購）

-- 2. 月預算（兩人共用一個：固定 id=1 的單列）
create table if not exists buylist_budget (
    id             int primary key default 1,
    monthly_budget numeric default 0,
    last_cleared   text default ''               -- 月初自動清已買用的「上次清除月份」YYYY-MM
);
insert into buylist_budget (id, monthly_budget) values (1, 0) on conflict (id) do nothing;
alter table buylist_budget add column if not exists last_cleared text default '';

-- 3. 權限（無登入，anon 全開）
alter table buylist_items  enable row level security;
alter table buylist_budget enable row level security;
drop policy if exists buylist_anon_all on buylist_items;
create policy buylist_anon_all on buylist_items for all to anon using (true) with check (true);
drop policy if exists buylist_budget_anon_all on buylist_budget;
create policy buylist_budget_anon_all on buylist_budget for all to anon using (true) with check (true);
grant usage on schema public to anon;
grant select, insert, update, delete on buylist_items, buylist_budget to anon;
grant usage, select on all sequences in schema public to anon;

-- 4. 即時同步
alter table buylist_items  replica identity full;
alter table buylist_budget replica identity full;
do $$ begin alter publication supabase_realtime add table buylist_items;  exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table buylist_budget; exception when duplicate_object then null; end $$;
