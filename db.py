import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "scout.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")  # 確保外鍵約束生效
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        -- ── 原有表格（維持不變）──
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            estimated_price REAL DEFAULT 0,
            added_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            purchased_date TEXT,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            year_month TEXT NOT NULL,
            budget_limit REAL NOT NULL,
            UNIQUE(user, year_month)
        );

        -- ── 旅程（最頂層，代表一整趟旅行）──
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- ── 行程項目（每一個景點 / 餐廳 / 活動）──
        CREATE TABLE IF NOT EXISTS itinerary_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            day_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'other',
            start_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            location TEXT DEFAULT '',
            address TEXT DEFAULT '',
            booking_ref TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            source TEXT DEFAULT 'manual',
            source_id INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        -- ── 調整紀錄（供日後查閱，現在先建起來）──
        CREATE TABLE IF NOT EXISTS trip_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            adjusted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            instruction TEXT NOT NULL,
            items_changed TEXT NOT NULL DEFAULT '[]'
        );
    """)
    conn.close()


# ── Trips CRUD ──

def create_trip(user, name, start_date, end_date, notes=""):
    """建立新旅程，回傳新旅程的 id"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO trips (user, name, start_date, end_date, notes) VALUES (?,?,?,?,?)",
        (user, name, start_date, end_date, notes)
    )
    trip_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trip_id


def get_trips(user):
    """取得某使用者的所有旅程，按開始日期排序"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM trips WHERE user=? ORDER BY start_date DESC",
        (user,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trip(trip_id):
    """取得單一旅程"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_trip(trip_id):
    """刪除旅程（行程項目會因 CASCADE 一起刪除）"""
    conn = get_conn()
    conn.execute("DELETE FROM trips WHERE id=?", (trip_id,))
    conn.commit()
    conn.close()


# ── Itinerary Items CRUD ──

def get_items_by_day(trip_id, day_number):
    """取得某天的所有行程項目，按 start_time 排序"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM itinerary_items
           WHERE trip_id=? AND day_number=?
           ORDER BY start_time ASC, sort_order ASC""",
        (trip_id, day_number)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_items(trip_id):
    """取得一趟旅程的所有行程項目，按天和時間排序"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM itinerary_items
           WHERE trip_id=?
           ORDER BY day_number ASC, start_time ASC, sort_order ASC""",
        (trip_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_item(trip_id, day_number, name, start_time, duration_minutes=60,
             category="other", location="", address="",
             booking_ref="", notes="", source="manual", source_id=None):
    """新增一個行程項目，回傳新項目的 id"""
    conn = get_conn()
    # sort_order 自動設為當天最後一個
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM itinerary_items WHERE trip_id=? AND day_number=?",
        (trip_id, day_number)
    ).fetchone()[0]
    cur = conn.execute(
        """INSERT INTO itinerary_items
           (trip_id, day_number, name, category, start_time, duration_minutes,
            location, address, booking_ref, notes, source, source_id, sort_order)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (trip_id, day_number, name, category, start_time, duration_minutes,
         location, address, booking_ref, notes, source, source_id, max_order + 1)
    )
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return item_id


def update_item_time(item_id, new_start_time):
    """更新單一項目的開始時間"""
    conn = get_conn()
    conn.execute(
        "UPDATE itinerary_items SET start_time=? WHERE id=?",
        (new_start_time, item_id)
    )
    conn.commit()
    conn.close()


def update_items_bulk(updates: list[dict]):
    """
    批次更新多個項目的時間，用於串聯調整。
    updates 格式：[{"id": 3, "start_time": "11:00"}, ...]
    """
    conn = get_conn()
    for u in updates:
        conn.execute(
            "UPDATE itinerary_items SET start_time=? WHERE id=?",
            (u["start_time"], u["id"])
        )
    conn.commit()
    conn.close()


def delete_item(item_id):
    """刪除單一行程項目"""
    conn = get_conn()
    conn.execute("DELETE FROM itinerary_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def log_adjustment(trip_id, instruction, items_changed: list):
    """記錄一次調整歷史"""
    import json
    conn = get_conn()
    conn.execute(
        "INSERT INTO trip_adjustments (trip_id, instruction, items_changed) VALUES (?,?,?)",
        (trip_id, instruction, json.dumps(items_changed, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


# ── Wishlist CRUD ──

def get_wishlist(user):
    """取得某使用者的所有待買清單，按新增時間倒序"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM wishlist WHERE user=? ORDER BY added_date DESC",
        (user,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_wishlist_item(user, name, category="", estimated_price=0.0, notes=""):
    """新增一筆待買項目，回傳新項目的 id"""
    from datetime import datetime
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO wishlist (user, name, category, estimated_price, added_date, status, notes)
           VALUES (?,?,?,?,?,?,?)""",
        (user, name, category, estimated_price,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "pending", notes)
    )
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return item_id


def update_wishlist_status(item_id, status):
    """更新待買項目的狀態（pending / purchased）"""
    from datetime import datetime
    conn = get_conn()
    purchased_date = datetime.now().strftime("%Y-%m-%d") if status == "purchased" else None
    conn.execute(
        "UPDATE wishlist SET status=?, purchased_date=? WHERE id=?",
        (status, purchased_date, item_id)
    )
    conn.commit()
    conn.close()


def delete_wishlist_item(item_id):
    """刪除單一待買項目"""
    conn = get_conn()
    conn.execute("DELETE FROM wishlist WHERE id=?", (item_id,))
    conn.commit()
    conn.close()