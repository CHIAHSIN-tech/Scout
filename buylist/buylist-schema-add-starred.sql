-- buylist-schema-add-starred.sql — 星號收藏功能的 schema 增量（冪等，可重跑）
-- 在 Stanley 的 Supabase 專案（kdmmjlaajqxjmiahfvos）SQL Editor 貼上、按 Run。
-- 對應 spec-buylist-starred.md

alter table buylist_items add column if not exists starred boolean default false;
