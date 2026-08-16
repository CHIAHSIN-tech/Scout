from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from fake_supabase import FakeSupabase  # noqa: E402

from scout_mcp.config import Endpoint  # noqa: E402
from scout_mcp.rest import PostgrestClient  # noqa: E402

SEED_TRIPS = [
    {
        "id": 1, "username": "stanley", "name": "沖繩四日",
        "start_date": "2026-09-01", "end_date": "2026-09-04", "notes": "",
    },
    {
        "id": 2, "username": "chia", "name": "京都秋遊",
        "start_date": "2026-11-10", "end_date": "2026-11-13", "notes": "",
    },
]

SEED_ITEMS = [
    {
        "id": 11, "trip_id": 1, "day_number": 1, "name": "美麗海水族館",
        "category": "attraction", "start_time": "10:00", "duration_minutes": 120,
        "location": "本部町", "address": "", "booking_ref": "", "notes": "",
        "confirm_required": True, "is_confirmed": False, "source": "manual",
    },
    {
        "id": 12, "trip_id": 1, "day_number": 1, "name": "國際通燒肉",
        "category": "restaurant", "start_time": "18:30", "duration_minutes": 90,
        "location": "那霸", "address": "", "booking_ref": "R-2211", "notes": "已訂位",
        "confirm_required": True, "is_confirmed": True, "source": "manual",
    },
    {
        "id": 13, "trip_id": 1, "day_number": None, "name": "琉球村",
        "category": "attraction", "start_time": None, "duration_minutes": None,
        "location": "", "address": "", "booking_ref": "", "notes": "",
        "confirm_required": False, "is_confirmed": False, "source": "manual",
    },
]

SEED_BUYLIST = [
    {"id": 21, "name": "登山襪", "price": 480, "quantity": 2, "bought": False,
     "urgency": "need", "category": "服飾", "tag": "日本", "note": "", "link": "",
     "added_by": "stanley", "starred": False, "actual_price": None, "this_month": True,
     "accessibility": "tw_easy", "recurring_cost": 0},
    {"id": 22, "name": "行動電源", "price": 1200, "quantity": 1, "bought": True,
     "urgency": "want", "category": "3C", "tag": "", "note": "", "link": "",
     "added_by": "chia", "starred": True, "actual_price": 999, "this_month": True,
     "accessibility": "tw_easy", "recurring_cost": 0},
]


@pytest.fixture
def fake() -> FakeSupabase:
    return FakeSupabase(
        {
            "trips": SEED_TRIPS,
            "itinerary_items": SEED_ITEMS,
            "buylist_items": SEED_BUYLIST,
        }
    )


@pytest.fixture
def itinerary_client(fake: FakeSupabase) -> PostgrestClient:
    return PostgrestClient(
        Endpoint(url="https://fake-itinerary.supabase.co", key="k", label="行程"),
        client=fake.client(),
    )


@pytest.fixture
def buylist_client(fake: FakeSupabase) -> PostgrestClient:
    return PostgrestClient(
        Endpoint(url="https://fake-buylist.supabase.co", key="k", label="購物"),
        client=fake.client(),
    )
